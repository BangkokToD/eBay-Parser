import asyncio
import contextlib
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from utils import (
    load_known_items,
    save_known_items,
    get_random_headers,
    get_file_hash,
    get_random_proxy,
    check_if_link_parsed,
    mark_link_as_parsed,
    extract_links,
    update_known_items_seen,
    prune_known_items,
)
from telegram_utils import notify_users_all, notify_users_photo_all
from config import (
    BLOCKED_PAGE_PATTERNS,
    BLOCKED_PAGE_SLEEP_SECONDS,
    BLOCK_RESOURCE_TYPES,
    BROWSER_CHANNEL,
    BROWSER_CONTEXT_LOCALE,
    BROWSER_CONTEXT_TIMEZONE_ID,
    BROWSER_CONTEXT_VIEWPORT,
    BROWSER_HEADLESS,
    BROWSER_RESTART_INTERVAL_MINUTES,
    CONTAINER_SELECTOR,
    CONTAINER_NOT_FOUND_SLEEP_SECONDS,
    CHECK_INTERVAL,
    PAGE_NAVIGATION_TIMEOUT_MS,
    PAGE_NAVIGATION_WAIT_UNTIL,
    DEBUG_HTML_SNIPPET_CHARS,
    DEBUG_NOTIFY_INTERVAL_SECONDS,
    DEBUG_SCREENSHOTS_DIR,
    DEBUG_SCREENSHOTS_ENABLED,
    DEBUG_SCREENSHOT_FULL_PAGE,
    EBAY_WARMUP_SLEEP_SECONDS,
    EBAY_WARMUP_URL,
    KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS,
    LINKS_FILE,
    LINKS_LIMIT,
    PROXY_LIMIT_ERROR_PATTERNS,
    PROXY_LIMIT_HTTP_STATUSES,
    PROXY_LIMIT_STOP_POLL_SECONDS,
    USE_PROXIES,
)

active_sessions = {}
known_items = load_known_items()
known_items_lock = asyncio.Lock()
last_known_items_cleanup_ts = 0.0
monitor_enabled_event = asyncio.Event()
proxy_limit_stop_event = asyncio.Event()
monitor_restart_requested = asyncio.Event()
proxy_limit_reason = ""
last_debug_notify_ts_by_name = {}


def normalize_error_text(value: object) -> str:
    """Нормализует текст ошибки для поиска сигнатур прокси-лимитов.

    Args:
        value: Любой объект ошибки или текст.

    Returns:
        Строка в нижнем регистре без лишних пробелов.
    """
    return " ".join(str(value or "").lower().split())


def is_proxy_limit_error(text: object) -> bool:
    """Проверяет, похож ли текст на ошибку лимита или оплаты прокси.

    Args:
        text: Текст ошибки, HTML страницы или сообщение Playwright.

    Returns:
        ``True``, если найден один из паттернов из конфига.
    """
    normalized_text = normalize_error_text(text)
    return any(
        normalize_error_text(pattern) in normalized_text
        for pattern in PROXY_LIMIT_ERROR_PATTERNS
    )


def is_proxy_limit_status(response: Any) -> bool:
    """Проверяет HTTP-статус ответа на признаки прокси-лимита.

    Args:
        response: Объект ответа Playwright или ``None``.

    Returns:
        ``True``, если статус входит в список критических статусов из конфига.
    """
    return bool(response and response.status in PROXY_LIMIT_HTTP_STATUSES)


async def detect_proxy_limit_from_page(page) -> str | None:
    """Ищет признаки лимита прокси в текущей странице.

    Args:
        page: Страница Playwright.

    Returns:
        Текст причины остановки или ``None``.
    """
    try:
        title = await page.title()
        content = await page.content()
        current_url = page.url
    except Exception as exc:
        error_text = str(exc)
        if is_proxy_limit_error(error_text):
            return f"Ошибка прокси: {error_text}"
        return None

    page_text = f"{title}\n{current_url}\n{content}"
    if is_proxy_limit_error(page_text):
        return "На странице найдены признаки исчерпания лимита или ошибки оплаты прокси."

    return None


def is_blocked_page_text(text: object) -> bool:
    """Проверяет текст страницы на признаки блокировки.

    Args:
        text: HTML, заголовок или текст ошибки.

    Returns:
        ``True``, если страница похожа на блокировку.
    """
    normalized_text = normalize_error_text(text)
    return any(
        normalize_error_text(pattern) in normalized_text
        for pattern in BLOCKED_PAGE_PATTERNS
    )


def should_send_debug_notification(name: str) -> bool:
    """Проверяет, можно ли отправлять debug-уведомление по ссылке.

    Args:
        name: Название ссылки.

    Returns:
        ``True``, если с прошлого уведомления прошло достаточно времени.
    """
    now_ts = time.monotonic()
    last_ts = last_debug_notify_ts_by_name.get(name, 0.0)

    if now_ts - last_ts < DEBUG_NOTIFY_INTERVAL_SECONDS:
        return False

    last_debug_notify_ts_by_name[name] = now_ts
    return True


def build_debug_file_prefix(name: str, reason: str) -> str:
    """Создаёт безопасный префикс имени debug-файла.

    Args:
        name: Название ссылки.
        reason: Причина создания debug-файла.

    Returns:
        Безопасный префикс имени файла.
    """
    source = f"{name}|{reason}|{time.time()}"
    digest = hashlib.md5(source.encode("utf-8")).hexdigest()[:12]
    return f"{int(time.time())}_{digest}"


async def collect_page_debug_text(page) -> str:
    """Собирает краткий debug-текст текущей страницы.

    Args:
        page: Страница Playwright.

    Returns:
        Текст с URL, title и фрагментом HTML.
    """
    try:
        title = await page.title()
    except Exception as exc:
        title = f"<title unavailable: {exc}>"

    try:
        current_url = page.url
    except Exception as exc:
        current_url = f"<url unavailable: {exc}>"

    try:
        content = await page.content()
    except Exception as exc:
        content = f"<content unavailable: {exc}>"

    snippet = content[:DEBUG_HTML_SNIPPET_CHARS]
    return f"URL: {current_url}\nTITLE: {title}\nHTML:\n{snippet}"


async def save_debug_artifacts(page, name: str, reason: str) -> tuple[str | None, str]:
    """Сохраняет debug-скриншот и краткий HTML-фрагмент страницы.

    Args:
        page: Страница Playwright.
        name: Название ссылки.
        reason: Причина сохранения.

    Returns:
        Кортеж ``(screenshot_path, debug_text)``.
    """
    debug_text = await collect_page_debug_text(page)

    if not DEBUG_SCREENSHOTS_ENABLED:
        return None, debug_text

    debug_dir = Path(DEBUG_SCREENSHOTS_DIR)
    debug_dir.mkdir(parents=True, exist_ok=True)

    file_prefix = build_debug_file_prefix(name, reason)
    screenshot_path = debug_dir / f"{file_prefix}.png"
    html_path = debug_dir / f"{file_prefix}.txt"

    try:
        await page.screenshot(
            path=str(screenshot_path),
            full_page=DEBUG_SCREENSHOT_FULL_PAGE,
        )
    except Exception as exc:
        print(f"[ERROR] Не удалось сохранить debug screenshot: {exc}")
        screenshot_path = None

    try:
        html_path.write_text(debug_text, encoding="utf-8")
    except Exception as exc:
        print(f"[ERROR] Не удалось сохранить debug HTML: {exc}")

    return str(screenshot_path) if screenshot_path else None, debug_text


async def handle_container_not_found(page, name: str, reason: str) -> None:
    """Обрабатывает ситуацию, когда контейнер товаров eBay не найден.

    Args:
        page: Страница Playwright.
        name: Название ссылки.
        reason: Причина отсутствия контейнера.
    """
    screenshot_path, debug_text = await save_debug_artifacts(page, name, reason)
    blocked = is_blocked_page_text(debug_text)
    sleep_seconds = BLOCKED_PAGE_SLEEP_SECONDS if blocked else CONTAINER_NOT_FOUND_SLEEP_SECONDS

    print(f"[WARNING] ({name}) {reason}. Пауза {sleep_seconds} сек.")
    print(debug_text[:DEBUG_HTML_SNIPPET_CHARS])

    if should_send_debug_notification(name):
        caption = (
            "⚠️ Контейнер товаров eBay не найден.\n\n"
            f"Ссылка: {name}\n"
            f"Причина: {reason}\n"
            f"Похоже на блокировку: {'да' if blocked else 'нет'}\n"
            f"Пауза перед повтором: {sleep_seconds} сек."
        )
        if screenshot_path:
            await notify_users_photo_all(screenshot_path, caption)
        else:
            await notify_users_all(caption)

    await asyncio.sleep(sleep_seconds)


def is_monitoring_enabled() -> bool:
    """Проверяет, включён ли мониторинг пользователем.

    Returns:
        ``True``, если мониторинг разрешён и controller-loop может запускать
        браузерные задачи.
    """
    return monitor_enabled_event.is_set()


async def start_monitoring() -> bool:
    """Включает ручной мониторинг ссылок.

    Returns:
        ``True``, если мониторинг был выключен и теперь включён.
        ``False``, если мониторинг уже был активен.
    """
    global proxy_limit_reason

    was_proxy_limited = proxy_limit_stop_event.is_set()

    if monitor_enabled_event.is_set() and not was_proxy_limited:
        return False

    proxy_limit_reason = ""
    proxy_limit_stop_event.clear()
    monitor_enabled_event.set()
    monitor_restart_requested.set()

    if was_proxy_limited:
        await notify_users_all("▶️ Поиск снова запущен.")

    return True


async def stop_monitoring(reason: str | None = None) -> bool:
    """Останавливает ручной мониторинг и закрывает активные сессии.

    Args:
        reason: Причина остановки для логов.

    Returns:
        ``True``, если мониторинг был активен или были активные задачи.
    """
    global proxy_limit_reason

    was_active = monitor_enabled_event.is_set() or bool(active_sessions)

    monitor_enabled_event.clear()
    monitor_restart_requested.clear()
    proxy_limit_stop_event.clear()
    proxy_limit_reason = ""

    await cancel_active_sessions(reason=reason or "ручная остановка")

    return was_active


async def restart_monitoring_with_new_proxies() -> None:
    """Перезапускает активные сессии после замены списка прокси.

    Если мониторинг сейчас выключен, функция ничего не делает. Если мониторинг
    включён, текущие браузерные задачи закрываются, а controller-loop создаёт
    новые задачи на следующем цикле уже с обновлённым ``proxies.json``.
    """
    if not monitor_enabled_event.is_set():
        return

    proxy_limit_stop_event.clear()
    monitor_restart_requested.set()
    await cancel_active_sessions(reason="замена списка прокси")


async def stop_monitoring_due_to_proxy_limit(reason: str) -> None:
    """Останавливает браузерный мониторинг из-за проблемы с прокси.

    Args:
        reason: Причина остановки для логов и Telegram-уведомления.
    """
    global proxy_limit_reason

    if proxy_limit_stop_event.is_set():
        return

    proxy_limit_reason = reason
    proxy_limit_stop_event.set()
    monitor_enabled_event.clear()
    monitor_restart_requested.clear()

    print(f"[CRITICAL] Поиск остановлен из-за прокси: {reason}")
    await notify_users_all(
        "⛔ Поиск остановлен.\n\n"
        "Причина: похоже, истёк лимит прокси или прокси требует пополнения.\n\n"
        f"Детали: {reason}\n\n"
        "Пополните прокси и нажмите «▶️ Старт» в меню бота."
    )


async def resume_proxy_limited_monitoring() -> bool:
    """Возобновляет мониторинг после ручного пополнения прокси.

    Returns:
        ``True``, если мониторинг был остановлен и теперь возобновлён.
        ``False``, если мониторинг уже был активен.
    """
    return await start_monitoring()

async def cancel_active_sessions(reason: str = "остановка мониторинга") -> None:
    """Отменяет все активные задачи мониторинга ссылок.


    Args:
        reason: Причина остановки для логов.
    """
    tasks = []

    for url, task in list(active_sessions.items()):
        print(f"[INFO] Останавливаем мониторинг ({reason}): {url}")
        task.cancel()
        tasks.append(task)

    active_sessions.clear()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def block_heavy_resource(route) -> None:
    """Блокирует тяжёлые ресурсы страницы для экономии прокси-трафика.

    Args:
        route: Playwright route.
    """
    blocked_types = {item.lower().strip() for item in BLOCK_RESOURCE_TYPES}
    resource_type = route.request.resource_type.lower()

    try:
        if resource_type in blocked_types:
            await route.abort()
            return

        await route.continue_()
    except Exception:
        # Во время закрытия браузера route может стать недоступным.
        # Ошибка здесь не должна валить мониторинг.
        pass


async def check_proxy_limit_or_stop(response: Any, page, name: str) -> bool:
    """Проверяет ответ/страницу и останавливает поиск при лимите прокси.

    Args:
        response: Ответ Playwright после ``goto`` или ``reload``.
        page: Текущая страница Playwright.
        name: Название ссылки для логов.

    Returns:
        ``True``, если можно продолжать мониторинг.
        ``False``, если мониторинг остановлен.
    """
    if is_proxy_limit_status(response):
        await stop_monitoring_due_to_proxy_limit(
            f"HTTP {response.status} при проверке «{name}»."
        )
        return False

    page_reason = await detect_proxy_limit_from_page(page)
    if page_reason:
        await stop_monitoring_due_to_proxy_limit(f"{page_reason} Ссылка: «{name}».")
        return False

    return True


async def persist_seen_links(raw_links: set[str], notify_new: bool) -> None:
    """Сохраняет найденные ссылки и отправляет уведомления по новым товарам.

    Args:
        raw_links: Ссылки, полученные со страницы.
        notify_new: Нужно ли отправлять уведомления по новым ссылкам.
    """
    global last_known_items_cleanup_ts

    async with known_items_lock:
        new_links = update_known_items_seen(known_items, raw_links)

        now_ts = time.monotonic()
        should_cleanup = (
            KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS > 0
            and now_ts - last_known_items_cleanup_ts >= KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS
        )

        if should_cleanup:
            removed_count = prune_known_items(known_items)
            last_known_items_cleanup_ts = now_ts
            if removed_count:
                print(f"[INFO] known_items.json: удалено старых записей: {removed_count}")

        save_known_items(known_items)

    if notify_new:
        for link in sorted(new_links):
            await notify_users_all(link)


def should_restart_browser(session_started_at: float) -> bool:
    """Проверяет, пора ли планово перезапускать Chromium.

    Args:
        session_started_at: Время старта браузерной сессии из ``time.monotonic()``.

    Returns:
        ``True``, если сессия старше лимита из конфига.
    """
    if BROWSER_RESTART_INTERVAL_MINUTES <= 0:
        return False

    restart_interval_seconds = BROWSER_RESTART_INTERVAL_MINUTES * 60
    return time.monotonic() - session_started_at >= restart_interval_seconds


def get_proxy_session_label(proxy: dict | None) -> str:
    """Возвращает безопасную метку proxy-сессии без раскрытия пароля.

    Args:
        proxy: Настройки прокси из ``proxies.json``.

    Returns:
        Строка с server и session ID, если он есть.
    """
    if not proxy:
        return "proxy=None"

    password = str(proxy.get("password", ""))
    session_id = "unknown"

    if "_session-" in password:
        session_id = password.split("_session-", 1)[1].split("_", 1)[0]

    return f"server={proxy.get('server')}, session={session_id}"


async def log_browser_public_ip(context, name: str, proxy: dict | None) -> None:
    """Логирует внешний IP браузера и выбранную proxy-сессию.

    Args:
        context: Контекст Playwright.
        name: Название ссылки для логов.
        proxy: Настройки прокси из ``proxies.json``.
    """
    page = None

    try:
        page = await context.new_page()
        await page.goto(
            "https://api.ipify.org?format=json",
            timeout=30000,
            wait_until="domcontentloaded",
        )
        body = await page.text_content("body")
        print(f"[DEBUG] ({name}) Proxy: {get_proxy_session_label(proxy)}")
        print(f"[DEBUG] ({name}) Browser public IP: {body}")
    except Exception as exc:
        print(f"[DEBUG] ({name}) Не удалось проверить IP браузера: {exc}")
    finally:
        if page:
            with contextlib.suppress(Exception):
                await page.close()


async def warmup_ebay_session(page, name: str) -> None:
    """Открывает главную eBay перед поиском.

    Args:
        page: Страница Playwright.
        name: Название ссылки для логов.
    """
    try:
        print(f"[INFO] ({name}) Прогрев eBay-сессии: {EBAY_WARMUP_URL}")
        await page.goto(
            EBAY_WARMUP_URL,
            timeout=PAGE_NAVIGATION_TIMEOUT_MS,
            wait_until=PAGE_NAVIGATION_WAIT_UNTIL,
        )
        await asyncio.sleep(EBAY_WARMUP_SLEEP_SECONDS)
    except Exception as exc:
        print(f"[WARNING] ({name}) Прогрев eBay не удался: {exc}")


def get_unique_links(data: list[dict]) -> list[dict]:
    """Возвращает список ссылок без дублей.

    Args:
        data: Содержимое ``links.json``.

    Returns:
        Список уникальных ссылок с сохранением первого названия.
    """
    unique_links = {}

    for item in data:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()
        if not url or url in unique_links:
            continue

        unique_links[url] = {
            "name": str(item.get("name") or url).strip(),
            "url": url,
        }

    return list(unique_links.values())


async def monitor_page(name, url):
    first_run = not check_if_link_parsed(name)

    while True:
        if proxy_limit_stop_event.is_set() or not monitor_enabled_event.is_set():
            print(f"[INFO] ({name}) Поиск остановлен до ручного запуска")
            return

        headers = get_random_headers()
        proxy = get_random_proxy() if USE_PROXIES else None
        browser = None
        try:
            print(f"[INFO] ({name}) Запуск браузера")
            async with async_playwright() as p:
                launch_kwargs = {"headless": BROWSER_HEADLESS}

                if BROWSER_CHANNEL:
                    launch_kwargs["channel"] = BROWSER_CHANNEL

                if proxy:
                    launch_kwargs["proxy"] = proxy

                browser = await p.chromium.launch(**launch_kwargs)
                session_started_at = time.monotonic()

                context_options = {
                    **headers,
                    "locale": BROWSER_CONTEXT_LOCALE,
                    "timezone_id": BROWSER_CONTEXT_TIMEZONE_ID,
                    "viewport": BROWSER_CONTEXT_VIEWPORT,
                }

                context = await browser.new_context(**context_options)

                if BLOCK_RESOURCE_TYPES:
                    await context.route("**/*", block_heavy_resource)

                await log_browser_public_ip(context, name, proxy)

                page = await context.new_page()
                await page.set_extra_http_headers(headers["extra_http_headers"])

                await warmup_ebay_session(page, name)

                response = await page.goto(
                    url,
                    timeout=PAGE_NAVIGATION_TIMEOUT_MS,
                    wait_until=PAGE_NAVIGATION_WAIT_UNTIL,
                )
                if not await check_proxy_limit_or_stop(response, page, name):
                    return

                try:
                    await page.wait_for_selector(CONTAINER_SELECTOR, timeout=15000)
                except PlaywrightTimeout:
                    if not await check_proxy_limit_or_stop(None, page, name):
                        return
                    await handle_container_not_found(
                        page,
                        name,
                        "Контейнер не найден после первичной загрузки",
                    )
                    continue

                raw_links = await extract_links(page, CONTAINER_SELECTOR, limit=LINKS_LIMIT)

                if first_run:
                    print(f"[INFO] ({name}) Первый запуск — ссылки сохраняются, но не отправляются")
                    await persist_seen_links(raw_links, notify_new=False)
                    mark_link_as_parsed(name)
                    first_run = False
                else:
                    await persist_seen_links(raw_links, notify_new=True)

                # 🔁 Повторная проверка
                while True:
                    try:
                        if proxy_limit_stop_event.is_set() or not monitor_enabled_event.is_set():
                            print(f"[INFO] ({name}) Поиск остановлен до ручного запуска")
                            return

                        if should_restart_browser(session_started_at):
                            print(f"[INFO] ({name}) Плановый перезапуск браузера")
                            break

                        response = await page.reload(
                            timeout=PAGE_NAVIGATION_TIMEOUT_MS,
                            wait_until=PAGE_NAVIGATION_WAIT_UNTIL,
                        )
                        if not await check_proxy_limit_or_stop(response, page, name):
                            return

                        await page.wait_for_selector(CONTAINER_SELECTOR, timeout=15000)
                        raw_links = await extract_links(page, CONTAINER_SELECTOR, limit=LINKS_LIMIT)
                        await persist_seen_links(raw_links, notify_new=True)
                        await asyncio.sleep(CHECK_INTERVAL)
                    except PlaywrightTimeout:
                        if not await check_proxy_limit_or_stop(None, page, name):
                            return
                        await handle_container_not_found(
                            page,
                            name,
                            "Контейнер исчез после перезагрузки страницы",
                        )
                        break

        except asyncio.CancelledError:
            print(f"[INFO] ({name}) Мониторинг остановлен")
            raise
        except Exception as e:
            if is_proxy_limit_error(e):
                await stop_monitoring_due_to_proxy_limit(f"Ошибка браузера/прокси: {e}")
                return

            print(f"[ERROR] ({name}) → {e}")
        finally:
            if browser:
                with contextlib.suppress(Exception):
                    await browser.close()
            await asyncio.sleep(1)


async def monitor_links():
    prev_hash = ""
    while True:
        try:
            if proxy_limit_stop_event.is_set():
                monitor_enabled_event.clear()
                await cancel_active_sessions(reason="прокси-лимит")
                prev_hash = ""
                await asyncio.sleep(PROXY_LIMIT_STOP_POLL_SECONDS)
                continue

            if not monitor_enabled_event.is_set():
                await cancel_active_sessions(reason="мониторинг выключен")
                prev_hash = ""
                await asyncio.sleep(3)
                continue

            if monitor_restart_requested.is_set():
                print("[INFO] Перезапуск мониторинга")
                monitor_restart_requested.clear()
                prev_hash = ""
                await cancel_active_sessions(reason="перезапуск мониторинга")

            links_hash = get_file_hash(LINKS_FILE)
            if links_hash != prev_hash:
                print("[INFO] Обнаружены изменения в links.json — пересоздаём сессии")
                prev_hash = links_hash
                
                with open(LINKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data = get_unique_links(data)

                new_keys = set(item["url"] for item in data)
                old_keys = set(active_sessions.keys())

                to_stop = old_keys - new_keys
                to_start = new_keys - old_keys

                for key in to_stop:
                    print(f"[INFO] Останавливаем мониторинг: {key}")
                    active_sessions[key].cancel()
                    del active_sessions[key]

                for item in data:
                    if item["url"] in to_start:
                        print(f"[INFO] Запускаем мониторинг: {item['name']}")
                        task = asyncio.create_task(monitor_page(item["name"], item["url"]))
                        active_sessions[item["url"]] = task

            await asyncio.sleep(3)

        except Exception as e:
            print("[ERROR] monitor_links:", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(monitor_links())
