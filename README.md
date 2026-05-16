# 🤖 eBay Link Monitor Telegram Bot
Асинхронный Telegram-бот для отслеживания новых товаров на eBay по заданным ссылкам. Работает в реальном времени, поддерживает авторизацию по ключу, защищён от блокировок (прокси, заголовки), и управляется прямо через Telegram.
---
## 🚀 Возможности
- Добавление/удаление eBay-ссылок через Telegram
- Уведомления при появлении новых товаров
- Авторизация пользователей по ключу
- Асинхронный браузер на Playwright
- Поддержка прокси, заголовков, анти-403
- Отдельный браузер под каждую ссылку
- Авто-обнаружение изменений в `links.json`
---
## 📁 Структура проекта
├── bot.py # Telegram-бот: FSM, команды, кнопки
├── browser_manager.py # Мониторинг ссылок через Playwright
├── telegram_utils.py # Отправка уведомлений
├── utils.py # Вспомогательные функции
├── config.py # Все настройки
├── authorized.json # Авторизованные пользователи
├── proxies.json # Прокси (если включены)
├── links.json # Добавленные пользователями ссылки
├── known_items.json # Уже замеченные товары
├── requirements.txt # Зависимости
└── README.md # Инструкция
---
## ⚙️ Быстрый старт
### 1. Установка Python
Убедитесь, что установлен Python 3.10+ и pip:
```
python3 --version
pip install --upgrade pip
```
2. Клонируем и устанавливаем зависимости
git clone https://github.com/yourname/ebay-monitor-bot.git
cd ebay-monitor-bot
```
pip install -r requirements.txt
```
3. Установка Playwright
```
playwright install
```
4. Настройка конфигурации
Открой config.py и укажи:
TELEGRAM_TOKEN = "твой_токен_бота"
ACCESS_KEY = "любой_ключ_для_авторизации"
⚙️ Остальные параметры:
    USE_PROXIES = True — если хочешь использовать прокси
    CONTAINER_SELECTOR — селектор контейнера eBay (оставить по умолчанию)
    CHECK_INTERVAL — задержка между проверками (сек)
5. Настройка файлов
Создай файлы, если они отсутствуют:
touch authorized.json links.json known_items.json
echo "[]" > authorized.json
echo "[]" > links.json
echo "[]" > known_items.json
🔐 Если используешь прокси — отредактируй proxies.json:
[
  {
    "server": "http://ip:port",
    "username": "user",
    "password": "pass"
  }
]
6. Запуск бота
```
python bot.py
```
После запуска:
    В Telegram: напиши /start
    Введите ключ (из ACCESS_KEY)
    Добавляй ссылки и жди уведомления

📦 requirements.txt
aiogram>=3.4.1
playwright>=1.42.0

🛡️ Примечания по защите
    Для обхода блокировок используется:
        Прокси (включаются в config.py)
        Заголовки Referer и Accept-Language
        Случайные User-Agent'ы
    Первый запуск каждой ссылки не отправляет уведомления — только сохраняет известные товары.

📬 Уведомления
Каждый новый товар отправляется всем авторизованным пользователям как обычная ссылка:
https://www.ebay.com/itm/1234567890
