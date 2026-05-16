import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from utils import (
    load_known_items, save_known_items,
    get_random_headers, get_file_hash,
    load_authorized_users, get_random_proxy,
    check_if_link_parsed, mark_link_as_parsed, 
    extract_links, normalize_url  # ← вот эти 2 функции
)
from telegram_utils import notify_users_all
from config import (
    CONTAINER_SELECTOR, CHECK_INTERVAL, LINKS_FILE,
    REFERERS, ACCEPT_LANGUAGES, USE_PROXIES  # ← добавь это
)

active_sessions = {}
known_items = load_known_items()
headers = get_random_headers()
proxy = get_random_proxy() if USE_PROXIES else None

async def monitor_page(name, url):
    first_run = not check_if_link_parsed(name)

    while True:
        headers = get_random_headers()
        proxy = get_random_proxy() if USE_PROXIES else None
        browser = None
        try:
            print(f"[INFO] ({name}) Запуск браузера")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(**headers)
                page = await context.new_page()
                await page.set_extra_http_headers(headers["extra_http_headers"])

                await page.goto(url, timeout=60000)

                try:
                    await page.wait_for_selector(CONTAINER_SELECTOR, timeout=15000)
                except PlaywrightTimeout:
                    print(f"[WARNING] ({name}) Контейнер не найден — перезапуск браузера")
                    continue

                raw_links = await extract_links(page, CONTAINER_SELECTOR)
                links = set([normalize_url(link) for link in raw_links])  # Нормализация

                if first_run:
                    print(f"[INFO] ({name}) Первый запуск — ссылки сохраняются, но не отправляются")
                    known_items.update(links)
                    save_known_items(known_items)
                    mark_link_as_parsed(name)
                    first_run = False
                else:
                    new_links = links - known_items
                    if new_links:
                        known_items.update(new_links)
                        save_known_items(known_items)
                        for link in new_links:
                            await notify_users_all(link)

                # 🔁 Повторная проверка
                while True:
                    try:
                        await page.reload(timeout=60000)
                        await page.wait_for_selector(CONTAINER_SELECTOR, timeout=15000)
                        raw_links = await extract_links(page, CONTAINER_SELECTOR)
                        links = set([normalize_url(link) for link in raw_links])  # Нормализация

                        new_links = links - known_items
                        if new_links:
                            known_items.update(new_links)
                            save_known_items(known_items)
                            for link in new_links:
                                await notify_users_all(link)
                        await asyncio.sleep(CHECK_INTERVAL)
                    except PlaywrightTimeout:
                        print(f"[WARNING] ({name}) Контейнер исчез — перезапуск браузера")
                        break

        except Exception as e:
            print(f"[ERROR] ({name}) → {e}")
        finally:
            try:
                await browser.close()
            except:
                pass
            await asyncio.sleep(1)


async def monitor_links():
    prev_hash = ""
    while True:
        try:
            links_hash = get_file_hash(LINKS_FILE)
            if links_hash != prev_hash:
                print("[INFO] Обнаружены изменения в links.json — пересоздаём сессии")
                prev_hash = links_hash
                
                with open(LINKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

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
