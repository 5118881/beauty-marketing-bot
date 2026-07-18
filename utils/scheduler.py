from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import LESSON_DAY_OF_WEEK, LESSON_SEND_HOUR, LESSON_SEND_MINUTE
from db.database import get_all_paid_users
from handlers.lessons import send_lesson_to_user, send_reminder


def schedule_lessons(scheduler: AsyncIOScheduler, bot: Bot):
    # Уроки каждое воскресенье в 10:00 МСК
    scheduler.add_job(
        send_weekly_lessons,
        trigger="cron",
        day_of_week=LESSON_DAY_OF_WEEK,
        hour=LESSON_SEND_HOUR,
        minute=LESSON_SEND_MINUTE,
        args=[bot],
        id="weekly_lessons",
        replace_existing=True
    )

    # Напоминание в среду (через 3 дня после воскресенья) в 12:00 МСК (09:00 UTC)
    scheduler.add_job(
        send_weekly_reminders,
        trigger="cron",
        day_of_week="wed",
        hour=9,
        minute=0,
        args=[bot],
        id="weekly_reminders",
        replace_existing=True
    )


async def send_weekly_lessons(bot: Bot):
    user_ids = await get_all_paid_users()
    for user_id in user_ids:
        try:
            await send_lesson_to_user(bot, user_id)
        except Exception as e:
            print(f"Ошибка урока для {user_id}: {e}")


async def send_weekly_reminders(bot: Bot):
    user_ids = await get_all_paid_users()
    for user_id in user_ids:
        try:
            await send_reminder(bot, user_id)
        except Exception as e:
            print(f"Ошибка напоминания для {user_id}: {e}")
