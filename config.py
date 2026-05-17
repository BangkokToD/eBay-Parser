from os import getenv

from dotenv import load_dotenv

load_dotenv()


def get_env_str(name: str, default: str = "") -> str:
    """Возвращает строковое значение переменной окружения.

    Args:
        name: Название переменной окружения.
        default: Значение по умолчанию.

    Returns:
        Строковое значение без лишних пробелов.
    """
    return getenv(name, default).strip()


def get_env_optional_str(name: str, default: str | None = None) -> str | None:
    """Возвращает опциональное строковое значение переменной окружения.

    Args:
        name: Название переменной окружения.
        default: Значение по умолчанию.

    Returns:
        Строка или ``None``, если значение пустое.
    """
    value = getenv(name)

    if value is None:
        return default

    value = value.strip()

    if not value or value.lower() in {"none", "null"}:
        return None

    return value


def get_env_int(name: str, default: int) -> int:
    """Возвращает целочисленное значение переменной окружения.

    Args:
        name: Название переменной окружения.
        default: Значение по умолчанию.

    Returns:
        Целое число из окружения или значение по умолчанию.
    """
    value = getenv(name)

    if value is None or not value.strip():
        return default

    return int(value)


def get_env_bool(name: str, default: bool) -> bool:
    """Возвращает булево значение переменной окружения.

    Args:
        name: Название переменной окружения.
        default: Значение по умолчанию.

    Returns:
        ``True`` или ``False``.
    """
    value = getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_env_list(name: str, default: list[str]) -> list[str]:
    """Возвращает список строк из переменной окружения.

    Значения разделяются запятыми. Пустая строка означает пустой список.

    Args:
        name: Название переменной окружения.
        default: Значение по умолчанию.

    Returns:
        Список строк.
    """
    value = getenv(name)

    if value is None:
        return default

    if not value.strip():
        return []

    return [item.strip() for item in value.split(",") if item.strip()]




# === Telegram ===
TELEGRAM_TOKEN = get_env_str("TELEGRAM_TOKEN")
ACCESS_KEY = get_env_str("ACCESS_KEY")
AUTHORIZED_USERS_FILE = get_env_str("AUTHORIZED_USERS_FILE", "authorized.json")

# === Файлы ===
LINKS_FILE = get_env_str("LINKS_FILE", "links.json")
KNOWN_ITEMS_FILE = get_env_str("KNOWN_ITEMS_FILE", "known_items.json")
PROXIES_FILE = get_env_str("PROXIES_FILE", "proxies.json")

# === eBay парсинг ===
CONTAINER_SELECTOR = get_env_str("CONTAINER_SELECTOR", "#srp-river-results > ul")
DEFAULT_EBAY_URL = get_env_str("DEFAULT_EBAY_URL", "https://by.ebay.com")
CHECK_INTERVAL = get_env_int("CHECK_INTERVAL", 90)
LINKS_LIMIT = get_env_int("LINKS_LIMIT", 20)
ITEM_CARD_SELECTOR = get_env_str("ITEM_CARD_SELECTOR", "li.s-card, li.s-item")
ITEM_LINK_SELECTOR = get_env_str(
    "ITEM_LINK_SELECTOR",
    "a.s-card__link[href*='/itm/'], a[href*='/itm/']",
)
ITEM_TITLE_SELECTOR = get_env_str(
    "ITEM_TITLE_SELECTOR",
    ".s-card__title .su-styled-text.primary.default, .s-card__title, .s-item__title",
)
ITEM_PRICE_SELECTOR = get_env_str("ITEM_PRICE_SELECTOR", ".s-card__price, .s-item__price")

# === Навигация браузера ===
PAGE_NAVIGATION_TIMEOUT_MS = get_env_int("PAGE_NAVIGATION_TIMEOUT_MS", 90000)
PAGE_NAVIGATION_WAIT_UNTIL = get_env_str("PAGE_NAVIGATION_WAIT_UNTIL", "domcontentloaded")

# Перед поисковой страницей открываем главную eBay, чтобы получить базовые cookies.
EBAY_WARMUP_URL = get_env_str("EBAY_WARMUP_URL", "https://www.ebay.com/")
EBAY_WARMUP_SLEEP_SECONDS = get_env_int("EBAY_WARMUP_SLEEP_SECONDS", 5)

# Для локальной диагностики можно поставить "chrome", чтобы Playwright запускал
# обычный установленный Chrome вместо bundled Chromium.
BROWSER_CHANNEL = get_env_optional_str("BROWSER_CHANNEL")

BROWSER_CONTEXT_LOCALE = get_env_str("BROWSER_CONTEXT_LOCALE", "en-US")
BROWSER_CONTEXT_TIMEZONE_ID = get_env_str("BROWSER_CONTEXT_TIMEZONE_ID", "America/New_York")
BROWSER_CONTEXT_VIEWPORT = {
    "width": get_env_int("BROWSER_CONTEXT_VIEWPORT_WIDTH", 1365),
    "height": get_env_int("BROWSER_CONTEXT_VIEWPORT_HEIGHT", 768),
}

# === Debug браузера ===
DEBUG_SCREENSHOTS_ENABLED = get_env_bool("DEBUG_SCREENSHOTS_ENABLED", True)
DEBUG_SCREENSHOTS_DIR = get_env_str("DEBUG_SCREENSHOTS_DIR", "debug_screenshots")
DEBUG_SCREENSHOT_FULL_PAGE = get_env_bool("DEBUG_SCREENSHOT_FULL_PAGE", True)
DEBUG_HTML_SNIPPET_CHARS = get_env_int("DEBUG_HTML_SNIPPET_CHARS", 1500)
DEBUG_NOTIFY_INTERVAL_SECONDS = get_env_int("DEBUG_NOTIFY_INTERVAL_SECONDS", 600)
CONTAINER_NOT_FOUND_SLEEP_SECONDS = get_env_int("CONTAINER_NOT_FOUND_SLEEP_SECONDS", 300)
BLOCKED_PAGE_SLEEP_SECONDS = get_env_int("BLOCKED_PAGE_SLEEP_SECONDS", 600)

BLOCKED_PAGE_PATTERNS = get_env_list(
    "BLOCKED_PAGE_PATTERNS",
    [
        "access denied",
        "errors.edgesuite.net",
        "you don't have permission to access",
        "captcha",
        "robot",
        "bot detection",
    ],
)

# === Экономия прокси-трафика ===
# Playwright resource types:
# document, stylesheet, image, media, font, script, texttrack,
# xhr, fetch, eventsource, websocket, manifest, other.
BLOCK_RESOURCE_TYPES = get_env_list("BLOCK_RESOURCE_TYPES", ["image", "media", "font"])

# === Остановка при лимитах прокси ===
# 402 — Payment Required, часто используется как признак неоплаченного доступа.
# 407 — Proxy Authentication Required.
PROXY_LIMIT_HTTP_STATUSES = [
    get_env_int("PROXY_LIMIT_HTTP_STATUS_PAYMENT_REQUIRED", 402),
    get_env_int("PROXY_LIMIT_HTTP_STATUS_PROXY_AUTH_REQUIRED", 407),
]

# Точные тексты зависят от провайдера прокси. После покупки прокси сюда
# желательно добавить реальные сообщения из их ошибок/страниц.
PROXY_LIMIT_ERROR_PATTERNS = get_env_list(
    "PROXY_LIMIT_ERROR_PATTERNS",
    [
        "traffic limit",
        "bandwidth limit",
        "quota exceeded",
        "quota has been reached",
        "not enough balance",
        "insufficient balance",
        "payment required",
        "proxy limit",
        "residential proxy limit",
        "subscription expired",
        "plan expired",
        "package expired",
        "407 proxy authentication required",
        "err_no_supported_proxies",
        "err_proxy_connection_failed",
        "err_tunnel_connection_failed",
    ],
)
PROXY_LIMIT_STOP_POLL_SECONDS = get_env_int("PROXY_LIMIT_STOP_POLL_SECONDS", 10)

# На сервере с Xvfb можно оставить False. Headless может сильнее палиться eBay.
BROWSER_HEADLESS = get_env_bool("BROWSER_HEADLESS", False)

# Принудительный рестарт браузера защищает от постепенного роста памяти Chromium.
BROWSER_RESTART_INTERVAL_MINUTES = get_env_int("BROWSER_RESTART_INTERVAL_MINUTES", 60)

# === TTL уже найденных товаров ===
# Товар удаляется из known_items.json, если не встречался на странице указанное число дней.
KNOWN_ITEMS_TTL_DAYS = get_env_int("KNOWN_ITEMS_TTL_DAYS", 30)
KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS = get_env_int("KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS", 3600)

# === Защита от блокировок ===
USE_PROXIES = get_env_bool("USE_PROXIES", True)

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.ebay.com/",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
]