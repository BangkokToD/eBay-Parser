import os
import json
import hashlib
import random
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pathlib import Path
from config import (
    LINKS_FILE, KNOWN_ITEMS_FILE,
    AUTHORIZED_USERS_FILE,
    REFERERS, ACCEPT_LANGUAGES, USE_PROXIES,
    PROXIES_FILE, KNOWN_ITEMS_TTL_DAYS
)


def get_utc_now_iso() -> str:
    """Возвращает текущее UTC-время в формате ISO 8601.

    Returns:
        Строка времени с суффиксом ``Z``.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_iso(value: str | None) -> datetime | None:
    """Преобразует ISO-строку в UTC datetime.

    Args:
        value: Значение из JSON или ``None``.

    Returns:
        Объект ``datetime`` в UTC или ``None``, если строку нельзя разобрать.
    """
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def normalize_known_item_meta(meta: object, now_iso: str) -> dict[str, str]:
    """Нормализует метаданные сохранённого товара.

    Args:
        meta: Старое или новое значение из ``known_items.json``.
        now_iso: Текущее время для заполнения отсутствующих полей.

    Returns:
        Словарь с ``first_seen_at`` и ``last_seen_at``.
    """
    if not isinstance(meta, dict):
        return {
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
        }

    first_seen_at = meta.get("first_seen_at") or now_iso
    last_seen_at = meta.get("last_seen_at") or first_seen_at

    return {
        "first_seen_at": first_seen_at,
        "last_seen_at": last_seen_at,
    }


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if "ebay.com" not in parsed.netloc:
            return url  # не eBay, не трогаем

        path = parsed.path
        if "/itm/" in path:
            # Обрезаем всё до /itm/ID
            return f"{parsed.scheme}://{parsed.netloc}{path.split('/itm/')[0]}/itm/{path.split('/itm/')[1].split('/')[0]}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception as e:
        print("[ERROR] normalize_url:", e)
        return url.strip()
        
def mark_link_as_parsed(name, links_file=LINKS_FILE):
    with open(links_file, "r", encoding="utf-8") as f:
        links = json.load(f)

    for link in links:
        if link.get("name") == name:
            link["parsed"] = True
            break

    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def check_if_link_parsed(name, links_file=LINKS_FILE):
    with open(links_file, "r", encoding="utf-8") as f:
        links = json.load(f)

    for link in links:
        if link.get("name") == name:
            return link.get("parsed", False)
    return False


def parse_proxy_line(line: str, line_number: int) -> tuple[dict | None, str | None]:
    """Разбирает одну строку прокси в формат Playwright.

    Args:
        line: Строка прокси из Telegram.
        line_number: Номер строки в исходном сообщении.

    Returns:
        Кортеж ``(proxy, error)``. Если строка валидна, ``error`` равен ``None``.
    """
    stripped_line = line.strip()
    if not stripped_line:
        return None, None

    if stripped_line.startswith("http://"):
        stripped_line = stripped_line.removeprefix("http://")
    elif stripped_line.startswith("https://"):
        stripped_line = stripped_line.removeprefix("https://")

    parts = stripped_line.split(":", 3)
    if len(parts) != 4:
        return None, (
            f"строка {line_number}: ожидается формат host:port:username:password"
        )

    host, port_raw, username, password = [part.strip() for part in parts]

    if not host:
        return None, f"строка {line_number}: host не может быть пустым"

    if "/" in host or " " in host:
        return None, f"строка {line_number}: host содержит недопустимые символы"

    if not port_raw.isdigit():
        return None, f"строка {line_number}: port должен быть числом"

    port = int(port_raw)
    if port < 1 or port > 65535:
        return None, f"строка {line_number}: port должен быть от 1 до 65535"

    if not username:
        return None, f"строка {line_number}: username не может быть пустым"

    if not password:
        return None, f"строка {line_number}: password не может быть пустым"

    return {
        "server": f"http://{host}:{port}",
        "username": username,
        "password": password,
    }, None


def parse_proxy_list_text(text: str) -> tuple[list[dict], list[str]]:
    """Разбирает многострочный список прокси.

    Пустые строки игнорируются. Если после удаления пустых строк список пустой,
    возвращается ошибка, чтобы случайно не очистить рабочий ``proxies.json``.

    Args:
        text: Многострочный текст от пользователя.

    Returns:
        Кортеж ``(proxies, errors)``.
    """
    proxies = []
    errors = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        proxy, error = parse_proxy_line(line, line_number)
        if error:
            errors.append(error)
            continue

        if proxy:
            proxies.append(proxy)

    if not proxies and not errors:
        errors.append("список прокси пустой")

    return proxies, errors


def save_proxies_atomic(proxies: list[dict]) -> None:
    """Атомарно сохраняет список прокси в ``PROXIES_FILE``.

    Args:
        proxies: Валидированный список прокси в формате Playwright.
    """
    target_path = Path(PROXIES_FILE)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f".{target_path.name}.tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(proxies, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, target_path)


def load_proxies():
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def get_random_proxy():
    if not os.path.exists(PROXIES_FILE):
        return None
    with open(PROXIES_FILE, "r") as f:
        proxies = json.load(f)
    if not proxies:
        return None
    return random.choice(proxies)

def load_links():
    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[ERROR] load_links:", e)
        return []

def get_file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

def load_known_items() -> dict[str, dict[str, str]]:
    """Загружает известные товары с обратной совместимостью.

    Поддерживает старый формат ``list[str]`` и новый формат
    ``dict[str, {"first_seen_at": str, "last_seen_at": str}]``.

    Returns:
        Словарь ссылок с датами первого и последнего обнаружения.
    """
    if not Path(KNOWN_ITEMS_FILE).exists():
        return {}

    with open(KNOWN_ITEMS_FILE, "r", encoding="utf-8") as f:
        try:
            raw_items = json.load(f)
        except Exception:
            return {}

    now_iso = get_utc_now_iso()

    if isinstance(raw_items, list):
        return {
            normalize_url(item): normalize_known_item_meta(None, now_iso)
            for item in raw_items
            if isinstance(item, str) and item.strip()
        }

    if not isinstance(raw_items, dict):
        return {}

    normalized_items = {}
    for url, meta in raw_items.items():
        if not isinstance(url, str) or not url.strip():
            continue
        normalized_items[normalize_url(url)] = normalize_known_item_meta(meta, now_iso)

    return normalized_items

def save_known_items(items):
    """Сохраняет известные товары в новом формате с метаданными.

    Args:
        items: Словарь нового формата. Для страховки также принимает старые
            коллекции ссылок и конвертирует их при сохранении.
    """
    now_iso = get_utc_now_iso()

    if isinstance(items, dict):
        normalized_items = {
            normalize_url(url): normalize_known_item_meta(meta, now_iso)
            for url, meta in items.items()
            if isinstance(url, str) and url.strip()
        }
    else:
        normalized_items = {
            normalize_url(url): normalize_known_item_meta(None, now_iso)
            for url in items
            if isinstance(url, str) and url.strip()
        }

    with open(KNOWN_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized_items, f, ensure_ascii=False, indent=2, sort_keys=True)

def update_known_items_seen(
    known_items: dict[str, dict[str, str]],
    links: set[str],
) -> set[str]:
    """Обновляет даты обнаружения и возвращает только новые ссылки.

    Args:
        known_items: Загруженный словарь известных товаров.
        links: Ссылки, найденные во время текущей проверки.

    Returns:
        Множество ссылок, которых раньше не было в ``known_items``.
    """
    now_iso = get_utc_now_iso()
    new_links = set()

    for link in links:
        normalized_link = normalize_url(link)
        if not normalized_link:
            continue

        current_meta = known_items.get(normalized_link)
        if current_meta is None:
            known_items[normalized_link] = {
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
            }
            new_links.add(normalized_link)
            continue

        normalized_meta = normalize_known_item_meta(current_meta, now_iso)
        normalized_meta["last_seen_at"] = now_iso
        known_items[normalized_link] = normalized_meta

    return new_links

def prune_known_items(
    known_items: dict[str, dict[str, str]],
    ttl_days: int = KNOWN_ITEMS_TTL_DAYS,
) -> int:
    """Удаляет товары, которые давно не встречались на странице.

    Args:
        known_items: Загруженный словарь известных товаров.
        ttl_days: Количество дней без повторного обнаружения до удаления.

    Returns:
        Количество удалённых записей.
    """
    if ttl_days <= 0:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    urls_to_delete = []

    for url, meta in known_items.items():
        normalized_meta = normalize_known_item_meta(meta, get_utc_now_iso())
        last_seen_at = parse_utc_iso(normalized_meta.get("last_seen_at"))

        # Некорректные даты не удаляем автоматически, чтобы не потерять данные
        # из-за ручной правки JSON.
        if last_seen_at is None:
            continue

        if last_seen_at < cutoff:
            urls_to_delete.append(url)

    for url in urls_to_delete:
        known_items.pop(url, None)

    return len(urls_to_delete)

def load_authorized_users():
    try:
        with open(AUTHORIZED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def get_random_headers() -> dict:
    """Возвращает HTTP-заголовки для браузерного контекста.

    Не подменяет User-Agent, потому что случайный User-Agent может не совпадать
    с реальным Chromium/Chrome и ухудшать браузерный отпечаток.

    Returns:
        Опции заголовков для Playwright ``new_context``.
    """
    return {
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

def generate_user_agent():
    chrome_build = f"{random.randint(100, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 999)}"
    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_build} Safari/537.36"
    )


def is_ebay_item_url(url: str) -> bool:
    """Проверяет, является ли ссылка карточкой товара eBay.

    Args:
        url: Ссылка для проверки.

    Returns:
        ``True``, если ссылка ведёт на товар ``/itm/``.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    return "ebay.com" in parsed.netloc and "/itm/" in parsed.path


async def extract_links(page, selector, limit=None):
    try:
        elements = await page.query_selector_all(f"{selector} a")

        raw_links = [await el.get_attribute("href") for el in elements if await el.get_attribute("href")]
        normalized = []

        for link in raw_links:
            if not link:
                continue
            normalized_link = normalize_url(link)
            if is_ebay_item_url(normalized_link):
                normalized.append(normalized_link)

        if limit:
            normalized = normalized[:limit]

        normalized = set(normalized)
        return normalized
    except Exception as e:
        print("[ERROR] extract_links:", e)
        return set()
