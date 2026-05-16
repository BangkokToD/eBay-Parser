# === Telegram ===
TELEGRAM_TOKEN = "твой_токен_бота"
ACCESS_KEY = "любой_ключ_для_авторизации"
AUTHORIZED_USERS_FILE = "authorized.json"

# === Файлы ===
LINKS_FILE = "links.json"
KNOWN_ITEMS_FILE = "known_items.json"

# === eBay парсинг ===
CONTAINER_SELECTOR = "#srp-river-results > ul"
DEFAULT_EBAY_URL = "https://by.ebay.com"
CHECK_INTERVAL = 15  # в секундах
LINKS_LIMIT = 20  # сколько ссылок проверять в последующих циклах

# === Защита от блокировок ===
USE_PROXIES = True

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.ebay.com/"
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
]

PROXIES_FILE = "proxies.json"  # путь к JSON-файлу с прокси