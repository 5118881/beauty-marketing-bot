import asyncio
from aiogram import Router, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import get_progress, has_access, set_homework_status, get_user
from lessons.content import get_lesson, total_lessons

router = Router()

# Мотивирующие фразы для напоминаний (через 3 дня)
WEEK_REMINDERS = [
    "Ещё есть время сдать домашнее задание! Куратор ждёт твою работу 💛",
    "Маленький шаг каждую неделю — и через месяц ты не узнаешь свой бизнес 🚀",
    "Ты уже вложила время в этот курс — не останавливайся на полпути! 💪",
]


async def send_lesson_to_user(bot: Bot, user_id: int):
    """Отправить урок ученику — каждое воскресенье."""
    if not await has_access(user_id):
        return

    progress = await get_progress(user_id)
    lesson_num = progress["current_lesson"]
    hw_status = progress["homework_status"]

    # Блокируем если ДЗ не проверено
    if hw_status in ("waiting", "pending_submit"):
        await bot.send_message(
            user_id,
            "⏳ *Новый урок пока заблокирован*\n\n"
            "Куратор ещё не проверил твоё домашнее задание.\n"
            "Как только проверит — сразу напишу! 💛",
            parse_mode="Markdown"
        )
        return

    if hw_status == "revision":
        await bot.send_message(
            user_id,
            "🔄 *Напоминание о доработке*\n\n"
            "Куратор попросил доработать домашнее задание — "
            "пришли исправленную версию, чтобы получить следующий урок.\n\n"
            "У тебя всё получится! 💪",
            parse_mode="Markdown"
        )
        return

    if lesson_num > total_lessons():
        await _send_course_complete(bot, user_id)
        return

    lesson = get_lesson(lesson_num)
    if not lesson:
        return

    await _send_full_lesson(bot, user_id, lesson)
    await set_homework_status(user_id, "pending_submit")


async def _send_full_lesson(bot: Bot, user_id: int, lesson: dict):
    """Отправляет все части урока последовательно."""
    lesson_num = lesson["number"]
    total = total_lessons()

    # ── 1. Анонс урока ────────────────────────────────────────────────
    await bot.send_message(
        user_id,
        f"🌸 *Доброе воскресенье!*\n\n"
        f"Твой новый урок уже здесь — урок {lesson_num} из {total}.\n"
        f"Заварь чай, устройся поудобнее ☕\n\n"
        f"_{lesson['title']}_",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)

    # ── 2. Видео ─────────────────────────────────────────────────────
    if lesson.get("video_file_id"):
        await bot.send_video(
            user_id,
            lesson["video_file_id"],
            caption=f"🎬 *{lesson['title']}*\n\nПосмотри урок и возвращайся — ниже ждут материалы!",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
    else:
        # Если видео ещё нет — заглушка
        await bot.send_message(
            user_id,
            "🎬 *Видеоурок скоро появится здесь*\n\n"
            "Пока читай конспект ниже — там всё самое важное!",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)

    # ── 3. Текст урока ────────────────────────────────────────────────
    await bot.send_message(user_id, lesson["text"], parse_mode="Markdown")
    await asyncio.sleep(1)

    # ── 4. Доп материалы ─────────────────────────────────────────────
    materials = lesson.get("materials", [])
    if materials:
        mat_lines = ["📚 *Дополнительные материалы к уроку:*\n"]
        url_materials = []
        pdf_materials = []

        for mat in materials:
            if mat["type"] == "url":
                url_materials.append(mat)
            elif mat["type"] == "pdf":
                pdf_materials.append(mat)

        # Ссылки — одним сообщением
        if url_materials:
            for mat in url_materials:
                mat_lines.append(f"• [{mat['title']}]({mat['url']})")
            await bot.send_message(
                user_id,
                "\n".join(mat_lines),
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            await asyncio.sleep(1)

        # PDF — каждый отдельным файлом
        for mat in pdf_materials:
            await bot.send_document(
                user_id,
                mat["file_id"],
                caption=mat["title"],
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)

    # ── 5. Шаблон ДЗ + задание ───────────────────────────────────────
    hw_template = lesson.get("hw_template", "")
    kb = InlineKeyboardBuilder()
    if hw_template and "ВСТАВЬ_ССЫЛКУ" not in hw_template:
        kb.button(text="📋 Открыть шаблон ДЗ", url=hw_template)
        kb.adjust(1)

    hw_text = (
        f"🏠 *Домашнее задание:*\n\n"
        f"{lesson['homework_task']}\n\n"
        f"📤 Пришли ответ прямо сюда — текстом, фото или голосовым.\n"
        f"Принимаю любой формат!"
    )

    await bot.send_message(
        user_id,
        hw_text,
        parse_mode="Markdown",
        reply_markup=kb.as_markup() if hw_template and "ВСТАВЬ_ССЫЛКУ" not in hw_template else None
    )
    await asyncio.sleep(1)

    # ── 6. Мотивация ─────────────────────────────────────────────────
    motivation = lesson.get("motivation", "")
    if motivation:
        progress_bar = _progress_bar(lesson["number"], total_lessons())
        await bot.send_message(
            user_id,
            f"💛 {motivation}\n\n{progress_bar}",
            parse_mode="Markdown"
        )


async def send_reminder(bot: Bot, user_id: int):
    """Напоминание через 3 дня если ДЗ не сдано."""
    if not await has_access(user_id):
        return

    progress = await get_progress(user_id)
    if progress["homework_status"] != "pending_submit":
        return  # уже сдал или ждёт проверки

    lesson_num = progress["current_lesson"]
    lesson = get_lesson(lesson_num)
    if not lesson:
        return

    reminder_text = lesson.get("reminder_3d", "")
    if not reminder_text:
        return

    hw_template = lesson.get("hw_template", "")
    kb = InlineKeyboardBuilder()
    if hw_template and "ВСТАВЬ_ССЫЛКУ" not in hw_template:
        kb.button(text="📋 Открыть шаблон ДЗ", url=hw_template)
        kb.adjust(1)

    await bot.send_message(
        user_id,
        f"⏰ *Напоминание*\n\n{reminder_text}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup() if hw_template and "ВСТАВЬ_ССЫЛКУ" not in hw_template else None
    )


async def _send_course_complete(bot: Bot, user_id: int):
    """Финальное сообщение после последнего урока."""
    user = await get_user(user_id)
    name = (user["full_name"] or "").split()[0] if user else ""

    await bot.send_message(
        user_id,
        f"🏆 *{name}, ты прошла весь курс Beauty Marketing!*\n\n"
        f"Это не просто цифра — ты реально сделала то, что большинство "
        f"откладывает бесконечно. Гордись собой! 🌸\n\n"
        f"Что дальше:\n"
        f"• Внедряй знания — по одному шагу в неделю\n"
        f"• Если есть вопросы — пиши, я на связи\n"
        f"• Буду рада отзыву о курсе 💛\n\n"
        f"Спасибо, что была со мной. Удачи в твоём бизнесе! 🚀",
        parse_mode="Markdown"
    )


def _progress_bar(current: int, total: int) -> str:
    """Визуальный прогресс-бар."""
    filled = "🟣" * current
    empty = "⚪️" * (total - current)
    percent = int(current / total * 100)
    return f"Твой прогресс: {filled}{empty} {percent}% ({current}/{total})"
