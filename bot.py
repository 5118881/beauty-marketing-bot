import asyncio
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import Any, Awaitable, Callable

from config import BOT_TOKEN, ADMIN_ID
from db.database import init_db, get_user
from handlers import start, lessons, homework
from utils.scheduler import schedule_lessons

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()


class NewUserMiddleware(BaseMiddleware):
    """Уведомляет куратора когда новый человек пишет боту."""
    async def __call__(self, handler: Callable, event: Any, data: dict) -> Any:
        if hasattr(event, "from_user") and event.from_user:
            user = event.from_user
            if user.id != ADMIN_ID:
                existing = await get_user(user.id)
                if not existing:
                    uname = f"@{user.username}" if user.username else "без username"
                    try:
                        await bot.send_message(
                            ADMIN_ID,
                            f"👤 *Новый человек написал боту*\n\n"
                            f"Имя: {user.full_name}\n"
                            f"Username: {uname}\n"
                            f"ID: `{user.id}`\n\n"
                            f"Если оплатил курс — открой доступ:\n`/grant {user.id}`",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
        return await handler(event, data)


async def main():
    await init_db()

    dp.include_router(start.router)
    dp.include_router(homework.router)
    dp.include_router(lessons.router)
    dp.message.middleware(NewUserMiddleware())

    schedule_lessons(scheduler, bot)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
