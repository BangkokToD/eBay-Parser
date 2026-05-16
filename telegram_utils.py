from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from config import TELEGRAM_TOKEN
from utils import load_authorized_users

bot = Bot(token=TELEGRAM_TOKEN)

async def notify_users_all(message: str):
    for user_id in load_authorized_users():
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"[ERROR] notify_users_all → {e}")