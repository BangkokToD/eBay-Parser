import os
import json
import hashlib
import random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pathlib import Path
from config import (
    LINKS_FILE, KNOWN_ITEMS_FILE,
    AUTHORIZED_USERS_FILE,
    REFERERS, ACCEPT_LANGUAGES, USE_PROXIES
)

PROXIES_FILE = "proxies.json"

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

def load_known_items():
    if not Path(KNOWN_ITEMS_FILE).exists():
        return set()
    with open(KNOWN_ITEMS_FILE, "r", encoding="utf-8") as f:
        try:
            return set(json.load(f))
        except:
            return set()

def save_known_items(items):
    with open(KNOWN_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(items)), f, ensure_ascii=False, indent=2)

def load_authorized_users():
    try:
        with open(AUTHORIZED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def get_random_headers():
    headers = {
        "user_agent": generate_user_agent(),
        "extra_http_headers": {
            "Referer": random.choice(REFERERS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES)
        }
    }
    return headers

def generate_user_agent():
    chrome_build = f"{random.randint(100, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 999)}"
    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_build} Safari/537.36"
    )

async def extract_links(page, selector, limit=None):
    try:
        elements = await page.query_selector_all(f"{selector} a")
        if limit:
            elements = elements[:limit]

        raw_links = [await el.get_attribute("href") for el in elements if await el.get_attribute("href")]
        normalized = set([normalize_url(link) for link in raw_links if link])
        return normalized
    except Exception as e:
        print("[ERROR] extract_links:", e)
        return set()
