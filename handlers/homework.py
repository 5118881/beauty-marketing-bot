from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from db.database import (
    get_progress, has_access, save_homework, set_homework_status,
    update_homework_review, get_homework, advance_lesson, get_user
)
from lessons.content import get_lesson, total_lessons

router = Router()

# Статусы ДЗ и их текстовое описание для ученика
HW_STATUS_TEXT = {
    "none":           "📅 Жди воскресенья — придёт новый урок",
    "pending_submit": "📝 Урок получен — отправь домашнее задание",
    "waiting":        "⏳ ДЗ отправлено, ожидает проверки куратора",
    "revision":       "🔄 Куратор попросил доработать — пришли исправленную версию",
    "approved":       "✅ ДЗ принято! Следующий урок придёт в воскресенье",
}


async def handle_hw_submission(message: types.Message, content_type: str,
                                file_id: str = None, text: str = None):
    user_id = message.from_user.id

    if not await has_access(user_id):
        await message.answer(
            "❌ У тебя нет доступа к курсу.\n\n"
            "Оплати курс на сайте ras4eshi.me/beautymarketing — "
            "куратор откроет доступ в течение дня 💛"
        )
        return

    progress = await get_progress(user_id)
    hw_status = progress["homework_status"]
    lesson_num = progress["current_lesson"]

    if hw_status == "none":
        await message.answer(
            "📅 Следующий урок придёт в *воскресенье в 10:00 МСК*.\n\n"
            "Пока можешь перечитать предыдущий урок или задать вопрос куратору командой /question",
            parse_mode="Markdown"
        )
        return

    if hw_status == "waiting":
        await message.answer(
            "⏳ Твоё домашнее задание уже отправлено!\n\n"
            "Куратор проверит и напишет тебе. Обычно это занимает 1-2 дня 💛"
        )
        return

    if hw_status == "approved":
        await message.answer(
            "✅ Твоё ДЗ уже принято!\n\n"
            "Следующий урок придёт в воскресенье. Если хочешь что-то уточнить — "
            "пиши куратору через /question"
        )
        return

    # pending_submit или revision — принимаем ДЗ
    hw_id = await save_homework(user_id, lesson_num, content_type, file_id, text)
    await set_homework_status(user_id, "waiting")

    is_revision = hw_status == "revision"
    await message.answer(
        "📬 *Домашнее задание отправлено!*\n\n"
        + ("Отлично, что доработала! " if is_revision else "")
        + "Куратор проверит и напишет тебе в течение 1-2 дней.\n\n"
        "Ты молодец, что не останавливаешься! 💛",
        parse_mode="Markdown"
    )

    # ── Пересылаем куратору ───────────────────────────────────────────
    user = await get_user(user_id)
    name = user["full_name"] or user["username"] or str(user_id)
    lesson = get_lesson(lesson_num)
    lesson_title = lesson["title"] if lesson else f"Урок {lesson_num}"

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принять", callback_data=f"hw_approve_{hw_id}_{user_id}")
    kb.button(text="🔄 На доработку", callback_data=f"hw_revision_{hw_id}_{user_id}")
    kb.adjust(2)

    tag = "🔄 ДОРАБОТКА" if is_revision else "📥 НОВОЕ ДЗ"
    caption = (
        f"{tag}\n\n"
        f"👤 {name}\n"
        f"🆔 `{user_id}`\n"
        f"📚 {lesson_title}\n"
        f"📎 Формат: {content_type}"
    )

    try:
        if content_type == "text":
            await message.bot.send_message(
                ADMIN_ID,
                f"{caption}\n\n💬 *Текст ДЗ:*\n{text}",
                parse_mode="Markdown",
                reply_markup=kb.as_markup()
            )
        elif content_type == "photo":
            await message.bot.send_photo(ADMIN_ID, file_id, caption=caption,
                                          parse_mode="Markdown", reply_markup=kb.as_markup())
        elif content_type == "voice":
            await message.bot.send_voice(ADMIN_ID, file_id, caption=caption,
                                          parse_mode="Markdown", reply_markup=kb.as_markup())
        elif content_type == "document":
            await message.bot.send_document(ADMIN_ID, file_id, caption=caption,
                                             parse_mode="Markdown", reply_markup=kb.as_markup())
        elif content_type == "video":
            await message.bot.send_video(ADMIN_ID, file_id, caption=caption,
                                          parse_mode="Markdown", reply_markup=kb.as_markup())
        elif content_type == "video_note":
            await message.bot.send_video_note(ADMIN_ID, file_id)
            await message.bot.send_message(ADMIN_ID, caption,
                                            parse_mode="Markdown", reply_markup=kb.as_markup())
    except Exception as e:
        print(f"Ошибка пересылки ДЗ куратору: {e}")


# ── Принимаем разные типы сообщений от ученика ───────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "text", text=message.text)

@router.message(F.photo)
async def on_photo(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "photo", file_id=message.photo[-1].file_id,
                                text=message.caption)

@router.message(F.voice)
async def on_voice(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "voice", file_id=message.voice.file_id)

@router.message(F.document)
async def on_document(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "document", file_id=message.document.file_id,
                                text=message.caption)

@router.message(F.video)
async def on_video(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "video", file_id=message.video.file_id)

@router.message(F.video_note)
async def on_video_note(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    await handle_hw_submission(message, "video_note", file_id=message.video_note.file_id)


# ── Вопрос куратору ───────────────────────────────────────────────────

@router.message(Command("question"))
async def ask_question(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Напиши вопрос после команды:\n"
            "/question Как правильно описать свою нишу?"
        )
        return
    question_text = parts[1]
    user = await get_user(message.from_user.id)
    name = user["full_name"] if user else str(message.from_user.id)
    await message.bot.send_message(
        ADMIN_ID,
        f"❓ *Вопрос от ученика*\n\n"
        f"👤 {name} (`{message.from_user.id}`)\n\n"
        f"{question_text}",
        parse_mode="Markdown"
    )
    await message.answer("Вопрос отправлен куратору! Отвечу в ближайшее время 💛")


# ── Куратор проверяет ДЗ ─────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("hw_approve_"))
async def approve_hw(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return

    _, _, hw_id, user_id = callback.data.split("_")
    hw_id, user_id = int(hw_id), int(user_id)

    await update_homework_review(hw_id, "approved")
    await advance_lesson(user_id)  # переходим к следующему уроку

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ ДЗ ученика {user_id} принято, урок разблокирован!")

    # Проверяем — последний ли урок был
    progress = await get_progress(user_id)
    from lessons.content import total_lessons
    if progress["current_lesson"] > total_lessons():
        from handlers.lessons import _send_course_complete
        await _send_course_complete(callback.bot, user_id)
    else:
        await callback.bot.send_message(
            user_id,
            "✅ *Куратор принял твоё домашнее задание!*\n\n"
            "Отличная работа! Ты двигаешься в правильном направлении 🎯\n\n"
            "📅 Следующий урок придёт в *воскресенье в 10:00 МСК*.\n"
            "До встречи! 💛",
            parse_mode="Markdown"
        )
    await callback.answer("Принято!")


@router.callback_query(lambda c: c.data and c.data.startswith("hw_revision_"))
async def revision_hw(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return

    _, _, hw_id, user_id = callback.data.split("_")
    hw_id, user_id = int(hw_id), int(user_id)

    await update_homework_review(hw_id, "revision")
    await set_homework_status(user_id, "revision")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Отмечено как «на доработку».\n\n"
        f"Напиши комментарий ученику:\n"
        f"`/feedback {user_id} твой комментарий`",
        parse_mode="Markdown"
    )
    await callback.answer("Отмечено!")


@router.message(Command("feedback"))
async def send_feedback(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: /feedback [user_id] [комментарий]")
        return
    try:
        user_id = int(parts[1])
        feedback_text = parts[2]
    except ValueError:
        await message.answer("❌ Неверный ID.")
        return

    await message.bot.send_message(
        user_id,
        f"🔄 *Куратор проверила домашнее задание*\n\n"
        f"💬 *Комментарий:*\n{feedback_text}\n\n"
        f"Доработай и пришли снова — у тебя всё получится! 💪",
        parse_mode="Markdown"
    )
    await message.answer(f"✅ Комментарий отправлен ученику {user_id}.")


@router.message(Command("reply"))
async def reply_to_student(message: types.Message):
    """Ответить на вопрос ученика. /reply [user_id] [текст]"""
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: /reply [user_id] [текст]")
        return
    try:
        user_id = int(parts[1])
        reply_text = parts[2]
    except ValueError:
        await message.answer("❌ Неверный ID.")
        return
    await message.bot.send_message(
        user_id,
        f"💬 *Ответ куратора:*\n\n{reply_text}",
        parse_mode="Markdown"
    )
    await message.answer(f"✅ Ответ отправлен ученику {user_id}.")
