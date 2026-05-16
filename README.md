# eBay Link Monitor Telegram Bot

Telegram-бот для мониторинга новых товаров на eBay по сохранённым поисковым ссылкам.

Бот управляется через Telegram: пользователь авторизуется по ключу, добавляет ссылки, удаляет ссылки, очищает список и получает уведомления о новых товарах.

Парсинг выполняется через Playwright и Chromium. Для каждой активной ссылки создаётся отдельная задача мониторинга и отдельный браузерный запуск.

## Возможности

* Авторизация пользователей по ключу доступа.
* Добавление eBay-ссылок через Telegram.
* Удаление отдельных ссылок.
* Очистка списка ссылок.
* Просмотр списка отслеживаемых ссылок.
* Мониторинг новых товаров на eBay.
* Отправка новых товаров всем авторизованным пользователям.
* Поддержка HTTP-прокси.
* Поддержка sticky residential proxy-сессий.
* Прогрев eBay-сессии через главную страницу перед поисковой страницей.
* Debug-скриншоты и HTML-фрагменты при проблемах с загрузкой страницы.
* TTL для `known_items.json`.
* Остановка мониторинга при признаках лимита или ошибки прокси.
* Ручной запуск мониторинга через кнопку `Старт`.

## Стек

* Python 3.12+
* aiogram 3
* Playwright
* Chromium / Chrome
* python-dotenv

## Структура проекта

```text
eBay Parser/
├── bot.py                  # Telegram-бот, FSM, кнопки, команды
├── browser_manager.py      # Мониторинг ссылок через Playwright
├── config.py               # Настройки проекта из .env
├── telegram_utils.py       # Отправка Telegram-уведомлений
├── utils.py                # JSON, прокси, ссылки, known_items
├── requirements.txt        # Python-зависимости
├── README.md               # Документация
├── .env.example            # Пример переменных окружения
├── .env                    # Локальные секреты, не коммитить
├── authorized.json         # Авторизованные Telegram-пользователи, не коммитить
├── links.json              # Список отслеживаемых ссылок, не коммитить
├── known_items.json        # Уже найденные товары, не коммитить
├── proxies.json            # Прокси, не коммитить
├── iproyal_list.txt        # Временный список прокси, не коммитить
└── debug_screenshots/      # Debug-артефакты, не коммитить
```

## Что нельзя коммитить

Нельзя коммитить:

```text
.env
.env.*
authorized.json
links.json
known_items.json
proxies.json
iproyal_list.txt
debug_screenshots/
.venv/
__pycache__/
*.log
```

Если реальные секреты уже попадали в переписку, скриншоты или публичный репозиторий, их нужно заменить:

* Telegram bot token;
* proxy username/password;
* access key, если он был публичным.

## Установка локально

### 1. Перейти в папку проекта

```bash
cd "eBay Parser"
```

Если папка ещё не создана, лучше использовать путь без пробелов:

```bash
mkdir -p ~/projects/ebay_parser
cd ~/projects/ebay_parser
```

### 2. Создать виртуальное окружение

```bash
python3.12 -m venv .venv
```

Если `python3.12` недоступен:

```bash
python3 -m venv .venv
```

Активировать окружение:

```bash
source .venv/bin/activate
```

Проверить:

```bash
which python
python --version
```

Ожидаемо путь должен быть внутри проекта:

```text
.../eBay Parser/.venv/bin/python
```

### 3. Обновить pip

```bash
python -m pip install --upgrade pip
```

### 4. Установить зависимости

```bash
pip install -r requirements.txt
```

В `requirements.txt` должны быть:

```text
aiogram>=3.4.1
playwright>=1.42.0
python-dotenv>=1.0.1
```

### 5. Установить браузер Playwright

Для обычной работы:

```bash
python -m playwright install chromium
```

Для теста с обычным Chrome:

```bash
python -m playwright install chrome
```

Если на сервере Ubuntu/Debian не хватает системных зависимостей:

```bash
python -m playwright install --with-deps chromium
```

## Настройка `.env`

Создать локальный `.env` из примера:

```bash
cp .env.example .env
```

Открыть файл:

```bash
nano .env
```

Минимально нужно заполнить:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
ACCESS_KEY=your_access_key
AUTHORIZED_USERS_FILE=authorized.json
LINKS_FILE=links.json
KNOWN_ITEMS_FILE=known_items.json
PROXIES_FILE=proxies.json
USE_PROXIES=True
BROWSER_HEADLESS=False
CHECK_INTERVAL=90
```

### Пример полного `.env`

```env
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token
ACCESS_KEY=your_access_key
AUTHORIZED_USERS_FILE=authorized.json

# Runtime files
LINKS_FILE=links.json
KNOWN_ITEMS_FILE=known_items.json
PROXIES_FILE=proxies.json

# eBay parsing
CONTAINER_SELECTOR="#srp-river-results > ul"
DEFAULT_EBAY_URL=https://by.ebay.com
CHECK_INTERVAL=90
LINKS_LIMIT=20

# Browser navigation
PAGE_NAVIGATION_TIMEOUT_MS=90000
PAGE_NAVIGATION_WAIT_UNTIL=domcontentloaded
EBAY_WARMUP_URL=https://www.ebay.com/
EBAY_WARMUP_SLEEP_SECONDS=5

# Browser mode
# Для eBay сейчас стабильнее BROWSER_HEADLESS=False.
# На сервере без экрана запускай через xvfb-run.
BROWSER_HEADLESS=False
BROWSER_CHANNEL=
BROWSER_RESTART_INTERVAL_MINUTES=60

# Browser context
BROWSER_CONTEXT_LOCALE=en-US
BROWSER_CONTEXT_TIMEZONE_ID=America/New_York
BROWSER_CONTEXT_VIEWPORT_WIDTH=1365
BROWSER_CONTEXT_VIEWPORT_HEIGHT=768

# Debug
DEBUG_SCREENSHOTS_ENABLED=True
DEBUG_SCREENSHOTS_DIR=debug_screenshots
DEBUG_SCREENSHOT_FULL_PAGE=True
DEBUG_HTML_SNIPPET_CHARS=1500
DEBUG_NOTIFY_INTERVAL_SECONDS=600
CONTAINER_NOT_FOUND_SLEEP_SECONDS=300
BLOCKED_PAGE_SLEEP_SECONDS=600
BLOCKED_PAGE_PATTERNS="access denied,errors.edgesuite.net,you don't have permission to access,captcha,robot,bot detection"

# Traffic saving
# Если eBay снова начнёт отдавать Access Denied, временно оставь пустым:
# BLOCK_RESOURCE_TYPES=
BLOCK_RESOURCE_TYPES=image,media,font

# Proxy limit detection
PROXY_LIMIT_HTTP_STATUS_PAYMENT_REQUIRED=402
PROXY_LIMIT_HTTP_STATUS_PROXY_AUTH_REQUIRED=407
PROXY_LIMIT_ERROR_PATTERNS="traffic limit,bandwidth limit,quota exceeded,quota has been reached,not enough balance,insufficient balance,payment required,proxy limit,residential proxy limit,subscription expired,plan expired,package expired,407 proxy authentication required,err_no_supported_proxies,err_proxy_connection_failed,err_tunnel_connection_failed"
PROXY_LIMIT_STOP_POLL_SECONDS=10

# Known items TTL
KNOWN_ITEMS_TTL_DAYS=30
KNOWN_ITEMS_CLEANUP_INTERVAL_SECONDS=3600

# Proxies
USE_PROXIES=True
```

## Настройка runtime JSON-файлов

Создать файлы, если их нет:

```bash
printf "[]\n" > authorized.json
printf "[]\n" > links.json
printf "{}\n" > known_items.json
printf "[]\n" > proxies.json
```

Важно: `known_items.json` должен быть объектом:

```json
{}
```

После работы бота он будет выглядеть примерно так:

```json
{
  "https://www.ebay.com/itm/1234567890": {
    "first_seen_at": "2026-05-16T20:33:03Z",
    "last_seen_at": "2026-05-16T21:03:47Z"
  }
}
```

## Настройка прокси

Бот читает прокси из файла `proxies.json`.

В `.env` должен быть путь:

```env
PROXIES_FILE=proxies.json
USE_PROXIES=True
```

Формат `proxies.json`:

```json
[
  {
    "server": "http://geo.iproyal.com:12321",
    "username": "PROXY_USERNAME",
    "password": "PROXY_PASSWORD_country-us_session-SESSIONID_lifetime-30m"
  }
]
```

### IPRoyal sticky residential proxy

Для IPRoyal строка из панели может выглядеть так:

```text
geo.iproyal.com:12321:USERNAME:PASSWORD_country-us_session-SESSIONID_lifetime-30m
```

В `proxies.json` её нужно разложить так:

```json
[
  {
    "server": "http://geo.iproyal.com:12321",
    "username": "USERNAME",
    "password": "PASSWORD_country-us_session-SESSIONID_lifetime-30m"
  }
]
```

Параметры:

```text
country-us          # гео США
session-SESSIONID   # sticky-сессия
lifetime-30m        # срок жизни сессии 30 минут
```

### Конвертация списка IPRoyal в `proxies.json`

Создать файл:

```bash
nano iproyal_list.txt
```

Вставить туда строки из IPRoyal в формате:

```text
geo.iproyal.com:12321:USERNAME:PASSWORD_country-us_session-SESSION1_lifetime-30m
geo.iproyal.com:12321:USERNAME:PASSWORD_country-us_session-SESSION2_lifetime-30m
```

Запустить конвертер:

```bash
python - <<'PY'
import json

items = []

with open("iproyal_list.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        host, port, username, password = line.split(":", 3)

        items.append({
            "server": f"http://{host}:{port}",
            "username": username,
            "password": password,
        })

with open("proxies.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Saved {len(items)} proxies to proxies.json")
PY
```

Проверить JSON:

```bash
python -m json.tool proxies.json
```

### Проверка прокси через Playwright

```bash
python - <<'PY'
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    with open("proxies.json", "r", encoding="utf-8") as f:
        proxy = json.load(f)[0]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=proxy)
        context = await browser.new_context()
        page = await context.new_page()

        for i in range(3):
            await page.goto("https://api.ipify.org?format=json", timeout=30000)
            print(f"IP #{i + 1}:", await page.text_content("body"))

        await browser.close()

asyncio.run(main())
PY
```

Для sticky-сессии IP должен быть одинаковым внутри одного теста:

```text
IP #1: {"ip":"x.x.x.x"}
IP #2: {"ip":"x.x.x.x"}
IP #3: {"ip":"x.x.x.x"}
```

Если IP меняется на каждом запросе, sticky-сессия настроена неправильно.

## Запуск локально

Проверить синтаксис:

```bash
python -m py_compile bot.py browser_manager.py telegram_utils.py utils.py config.py
```

Запустить бота:

```bash
python bot.py
```

В Telegram:

1. Написать боту `/start`.
2. Ввести ключ из `ACCESS_KEY`.
3. Нажать `Добавить`.
4. Ввести название ссылки.
5. Отправить eBay search URL.
6. Дождаться первого обхода.

## Как использовать бота

### Авторизация

Команда:

```text
/start
```

Если пользователь ещё не авторизован, бот попросит ключ доступа.

Ключ берётся из `.env`:

```env
ACCESS_KEY=your_access_key
```

После успешной авторизации Telegram ID пользователя сохраняется в:

```text
authorized.json
```

### Добавление ссылки

В меню нажать:

```text
Добавить
```

Порядок:

1. Бот попросит название ссылки.
2. Отправить удобное название.
3. Бот попросит саму ссылку.
4. Отправить eBay search URL.

Пример ссылки:

```text
https://www.ebay.com/sch/i.html?_nkw=lot&_sop=10
```

### Список ссылок

Кнопка:

```text
Список
```

Показывает все ссылки из `links.json`.

### Удаление ссылки

Кнопка:

```text
Удалить
```

Бот покажет список ссылок. Нужно выбрать ссылку для удаления.

### Очистка всех ссылок

Кнопка:

```text
Очистить всё
```

Полностью очищает `links.json`.

### Ручной запуск

Кнопка:

```text
Старт
```

Используется после остановки мониторинга из-за лимита или ошибки прокси.

## Первый запуск ссылки

Первый запуск новой ссылки не отправляет уведомления.

Он делает следующее:

1. Открывает eBay.
2. Прогревает сессию через главную страницу.
3. Открывает поисковую страницу.
4. Собирает текущие товары.
5. Сохраняет их в `known_items.json`.
6. Помечает ссылку как `parsed`.

Уведомления начнут приходить только по новым товарам, которых ещё нет в `known_items.json`.

## Проверка уведомлений

Можно удалить один товар из `known_items.json` и дождаться следующего цикла.

Сначала сделать backup:

```bash
cp known_items.json known_items.backup.json
```

Удалить один товар:

```bash
python - <<'PY'
import json

with open("known_items.json", "r", encoding="utf-8") as f:
    data = json.load(f)

key = next(iter(data))
data.pop(key)

with open("known_items.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Removed:", key)
PY
```

Запустить бота:

```bash
python bot.py
```

Если этот товар всё ещё есть на странице, бот должен отправить его как новый.

Вернуть backup:

```bash
mv known_items.backup.json known_items.json
```

## Деплой на сервер

Рекомендуемая ОС:

```text
Ubuntu 24.04 LTS
```

Рекомендуемый минимум:

```text
2 vCPU
4 GB RAM
40+ GB SSD
```

Для нескольких ссылок и Chromium лучше:

```text
2-4 vCPU
4-8 GB RAM
```

### 1. Подключиться к серверу

```bash
ssh root@SERVER_IP
```

### 2. Обновить систему

```bash
apt update
apt upgrade -y
```

### 3. Установить системные зависимости

```bash
apt install -y git python3 python3-venv python3-pip xvfb
```

### 4. Создать папку проекта

Лучше без пробелов:

```bash
mkdir -p /opt/ebay-parser
cd /opt/ebay-parser
```

### 5. Загрузить код

Вариант через git:

```bash
git clone YOUR_REPOSITORY_URL .
```

Или загрузить файлы вручную через `scp`/SFTP.

### 6. Создать venv на сервере

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 7. Установить зависимости

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 8. Установить Playwright browser

```bash
python -m playwright install chromium
```

Если нужны системные зависимости:

```bash
python -m playwright install --with-deps chromium
```

### 9. Создать `.env`

```bash
cp .env.example .env
nano .env
```

На сервере лучше использовать абсолютные пути:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
ACCESS_KEY=your_access_key

AUTHORIZED_USERS_FILE=/opt/ebay-parser/authorized.json
LINKS_FILE=/opt/ebay-parser/links.json
KNOWN_ITEMS_FILE=/opt/ebay-parser/known_items.json
PROXIES_FILE=/opt/ebay-parser/proxies.json

USE_PROXIES=True
BROWSER_HEADLESS=False
CHECK_INTERVAL=90
```

### 10. Создать runtime JSON-файлы

```bash
printf "[]\n" > authorized.json
printf "[]\n" > links.json
printf "{}\n" > known_items.json
printf "[]\n" > proxies.json
```

### 11. Заполнить `proxies.json`

```bash
nano proxies.json
```

Пример:

```json
[
  {
    "server": "http://geo.iproyal.com:12321",
    "username": "PROXY_USERNAME",
    "password": "PROXY_PASSWORD_country-us_session-SESSIONID_lifetime-30m"
  }
]
```

Проверить:

```bash
python -m json.tool proxies.json
```

### 12. Проверить запуск вручную

Так как `BROWSER_HEADLESS=False`, на сервере нужно запускать через Xvfb:

```bash
xvfb-run -a .venv/bin/python bot.py
```

Если бот запускается и в Telegram отвечает, можно настраивать systemd.

## Systemd service

Создать service-файл:

```bash
nano /etc/systemd/system/ebay-parser-bot.service
```

Содержимое:

```ini
[Unit]
Description=eBay Parser Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ebay-parser
ExecStart=/usr/bin/xvfb-run -a /opt/ebay-parser/.venv/bin/python /opt/ebay-parser/bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Применить:

```bash
systemctl daemon-reload
systemctl enable ebay-parser-bot
systemctl start ebay-parser-bot
```

Проверить статус:

```bash
systemctl status ebay-parser-bot
```

Смотреть логи:

```bash
journalctl -u ebay-parser-bot -f
```

Остановить:

```bash
systemctl stop ebay-parser-bot
```

Перезапустить:

```bash
systemctl restart ebay-parser-bot
```

## Headless и Xvfb

Сейчас для eBay стабильнее:

```env
BROWSER_HEADLESS=False
```

На локальном компьютере это откроет обычное окно браузера.

На сервере настоящего экрана нет, поэтому используется:

```bash
xvfb-run -a .venv/bin/python bot.py
```

Если поставить:

```env
BROWSER_HEADLESS=True
```

бот может снова получить `Access Denied`, даже если прокси рабочий.

## Debug-артефакты

Если бот не нашёл контейнер товаров, он сохраняет debug-файлы в:

```text
debug_screenshots/
```

Там могут быть:

```text
*.png
*.txt
```

В `.txt` лежит URL, title и HTML-фрагмент страницы.

Если в debug-файле:

```text
TITLE: Access Denied
errors.edgesuite.net
```

значит eBay/Akamai заблокировал текущий браузер/IP/сессию.

Если title нормальный, например:

```text
Und Lot for sale | eBay
```

значит страница открылась, а проблема может быть в селекторе или структуре выдачи.

## Частые проблемы

### `Access Denied`

Возможные причины:

* плохой proxy-IP;
* eBay режет текущую sticky-сессию;
* включён `BROWSER_HEADLESS=True`;
* заблокированы важные ресурсы;
* слишком частые проверки;
* слишком много одинаковых ссылок;
* грязная eBay-ссылка с tracking-параметрами.

Что делать:

1. Проверить прокси через обычный Chrome.
2. Оставить одну рабочую sticky-сессию в `proxies.json`.
3. Поставить `BROWSER_HEADLESS=False`.
4. Запускать на сервере через Xvfb.
5. Временно поставить:

```env
BLOCK_RESOURCE_TYPES=
```

6. Увеличить интервал:

```env
CHECK_INTERVAL=180
```

### `ERR_NO_SUPPORTED_PROXIES`

Обычно это неправильный формат прокси.

Правильно:

```json
{
  "server": "http://geo.iproyal.com:12321",
  "username": "USERNAME",
  "password": "PASSWORD_country-us_session-SESSIONID_lifetime-30m"
}
```

Неправильно:

```json
{
  "server": "geo.iproyal.com:12321"
}
```

`server` должен содержать `http://`.

### `chat not found`

Бот пытается отправить сообщение пользователю, которому не может писать.

Причины:

* пользователь не начинал диалог с ботом;
* пользователь заблокировал бота;
* ID в `authorized.json` устарел.

Решение:

* удалить проблемный ID из `authorized.json`;
* пользователь должен снова написать `/start`.

### Первый запуск не отправляет уведомления

Это нормально.

Первый запуск только сохраняет текущие товары в `known_items.json`.

### Прокси не подтягиваются

Проверить:

```bash
python - <<'PY'
from config import USE_PROXIES, PROXIES_FILE
from utils import get_random_proxy

print("USE_PROXIES =", USE_PROXIES)
print("PROXIES_FILE =", PROXIES_FILE)
print("PROXY =", get_random_proxy())
PY
```

Если `PROXY = None`, проверь:

* существует ли `proxies.json`;
* правильно ли указан `PROXIES_FILE` в `.env`;
* запускаешь ли бот из корня проекта;
* валидный ли JSON.

### Бот на сервере не открывает браузер

Если `BROWSER_HEADLESS=False`, нужен Xvfb:

```bash
xvfb-run -a .venv/bin/python bot.py
```

Для systemd `ExecStart` должен тоже использовать `xvfb-run`.

## Обслуживание

### Сменить sticky session

В `proxies.json` изменить часть:

```text
_session-XXXXXXXX
```

Например:

```text
_session-YzJ8Il52
```

на:

```text
_session-Ab12Cd34
```

После изменения перезапустить бота:

```bash
systemctl restart ebay-parser-bot
```

или локально:

```bash
Ctrl+C
python bot.py
```

### Очистить список ссылок

Через Telegram:

```text
Очистить всё
```

Или вручную:

```bash
printf "[]\n" > links.json
```

### Сбросить известные товары

```bash
printf "{}\n" > known_items.json
```

После этого первый запуск снова сохранит все текущие товары как уже известные и не отправит их.

### Сделать backup runtime-файлов

```bash
mkdir -p backups
cp authorized.json links.json known_items.json proxies.json backups/
```

## Быстрый локальный запуск с нуля

```bash
cd "eBay Parser"

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python -m playwright install chromium

cp .env.example .env

printf "[]\n" > authorized.json
printf "[]\n" > links.json
printf "{}\n" > known_items.json
printf "[]\n" > proxies.json

nano .env
nano proxies.json

python -m py_compile bot.py browser_manager.py telegram_utils.py utils.py config.py
python bot.py
```

## Быстрый серверный запуск с нуля

```bash
apt update
apt install -y git python3 python3-venv python3-pip xvfb

mkdir -p /opt/ebay-parser
cd /opt/ebay-parser

# Загрузить код проекта сюда.

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env

printf "[]\n" > authorized.json
printf "[]\n" > links.json
printf "{}\n" > known_items.json
printf "[]\n" > proxies.json

nano .env
nano proxies.json

python -m py_compile bot.py browser_manager.py telegram_utils.py utils.py config.py
xvfb-run -a .venv/bin/python bot.py
```

## Минимальный `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/

# Local env files
.env
.env.*
!.env.example

# Runtime state
authorized.json
links.json
known_items.json
proxies.json
iproyal_list.txt

# Debug/runtime artifacts
debug_screenshots/
*.log
logs/
tmp/
temp/

# Playwright
playwright-report/
test-results/

# OS/editor
.DS_Store
Thumbs.db
.idea/
.vscode/
```