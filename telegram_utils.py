import html
import json

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import FSInputFile
from config import AUTHORIZED_USERS_FILE, TELEGRAM_TOKEN
from utils import load_authorized_users

bot = Bot(token=TELEGRAM_TOKEN)


def is_unreachable_chat_error(error: Exception) -> bool:
    """Проверяет, что пользователю больше нельзя писать в Telegram.

    Args:
        error: Исключение aiogram.

    Returns:
        ``True``, если пользователя нужно убрать из списка уведомлений.
    """
    error_text = str(error).lower()
    return isinstance(error, (TelegramBadRequest, TelegramForbiddenError)) and (
        "chat not found" in error_text
        or "bot was blocked" in error_text
        or "user is deactivated" in error_text
    )


def remove_authorized_user(user_id: int) -> None:
    """Удаляет недоступного пользователя из ``authorized.json``.

    Args:
        user_id: Telegram ID пользователя.
    """
    users = load_authorized_users()
    filtered_users = [item for item in users if item != user_id]

    if filtered_users == users:
        return

    with open(AUTHORIZED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_users, f, ensure_ascii=False, indent=2)


def format_item_message(item: dict) -> str:
    """Формирует HTML-сообщение о новом товаре.

    Args:
        item: Словарь товара с ``url``, ``title`` и ``price``.

    Returns:
        HTML-строка для отправки в Telegram.
    """
    raw_url = str(item.get("url") or "").strip()
    safe_url = html.escape(raw_url, quote=True)

    raw_title = item.get("title")
    raw_price = item.get("price") or "Цена не найдена"

    safe_price = html.escape(str(raw_price), quote=False)

    if raw_title:
        safe_title = html.escape(str(raw_title), quote=False)
        return (
            f'<b><i><a href="{safe_url}">{safe_title}</a></i></b>\n'
            f"<i><u>{safe_price}</u></i>"
        )

    safe_display_url = html.escape(raw_url, quote=False)
    return (
        f'<a href="{safe_url}">{safe_display_url}</a>\n'
        "<b><i>Название не найдено</i></b>\n"
        f"<i><u>{safe_price}</u></i>"
    )


async def notify_item_all(item: dict) -> None:
    """Отправляет уведомление о новом товаре всем авторизованным пользователям.

    Args:
        item: Словарь товара с ``url``, ``title`` и ``price``.
    """
    message = format_item_message(item)

    for user_id in load_authorized_users():
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            if is_unreachable_chat_error(e):
                remove_authorized_user(user_id)
                print(f"[WARNING] notify_item_all: пользователь удалён из authorized.json: {user_id}")
                continue

            print(f"[ERROR] notify_item_all → {e}")


async def notify_users_all(message: str):
    for user_id in load_authorized_users():
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            if is_unreachable_chat_error(e):
                remove_authorized_user(user_id)
                print(f"[WARNING] notify_users_all: пользователь удалён из authorized.json: {user_id}")
                continue

            print(f"[ERROR] notify_users_all → {e}")
            

async def notify_users_photo_all(photo_path: str, caption: str = ""):
    """Отправляет фото всем авторизованным пользователям.

    Args:
        photo_path: Путь к локальному файлу изображения.
        caption: Подпись к изображению.
    """
    photo = FSInputFile(photo_path)

    for user_id in load_authorized_users():
        try:
            await bot.send_photo(chat_id=user_id, photo=photo, caption=caption[:1024])
        except Exception as e:
            if is_unreachable_chat_error(e):
                remove_authorized_user(user_id)
                print(f"[WARNING] notify_users_photo_all: пользователь удалён из authorized.json: {user_id}")
                continue

            print(f"[ERROR] notify_users_photo_all → {e}")


async def close_notify_bot_session() -> None:
    """Закрывает HTTP-сессию вспомогательного Telegram Bot.

    Нужна для корректного завершения процесса без ``Unclosed client session``.
    """
    await bot.session.close()
