from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from db.database import register_user, has_access, get_progress, get_all_users_for_admin, grant_access
from lessons.content import total_lessons

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name)

    if await has_access(user.id):
        progress = await get_progress(user.id)
        lesson = progress["current_lesson"]
        hw_status = progress["homework_status"]

        status_text = ""
        if hw_status == "waiting":
            status_text = "\n\n⏳ Твоё домашнее задание ожидает проверки."
        elif hw_status == "revision":
            status_text = "\n\n🔄 Куратор попросил доработать ДЗ. Отправь исправленную версию."
        elif hw_status == "approved":
            status_text = "\n\n✅ ДЗ принято! Следующий урок придёт в воскресенье."

        await message.answer(
            f"👋 С возвращением, {user.first_name}!\n\n"
            f"📚 Текущий урок: {lesson} из {total_lessons()}{status_text}\n\n"
            f"Используй /status для подробной информации.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Добро пожаловать на курс *{chr(171)}Beauty Marketing{chr(187)}*\n\n"
            f"После оплаты на сайте куратор откроет тебе доступ — "
            f"и в воскресенье придёт первый урок!\n\n"
            f"🌐 ras4eshi.ru/beautymarketing",
            parse_mode="Markdown"
        )


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    if not await has_access(user_id):
        await message.answer("❌ У тебя нет доступа к курсу.")
        return

    progress = await get_progress(user_id)
    lesson = progress["current_lesson"]
    hw_status = progress["homework_status"]

    hw_map = {
        "none": "📝 Жди воскресенья — придёт новый урок",
        "waiting": "⏳ ДЗ отправлено, ожидает проверки куратора",
        "revision": "🔄 Нужна доработка — проверь комментарий куратора",
        "approved": "✅ ДЗ принято! Следующий урок придёт в воскресенье",
    }

    await message.answer(
        f"📊 *Твой прогресс:*\n\n"
        f"📚 Урок: {lesson} из {total_lessons()}\n"
        f"🏠 Статус ДЗ: {hw_map.get(hw_status, '—')}\n\n"
        f"Уроки приходят каждое воскресенье в 10:00 МСК.",
        parse_mode="Markdown"
    )


# ── КОМАНДЫ АДМИНИСТРАТОРА ────────────────────────────────────────────

@router.message(Command("grant"))
async def cmd_grant(message: types.Message):
    """Открыть доступ ученику. Использование: /grant 123456789"""
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "Использование: /grant [user_id]\n\n"
            "Пример: /grant 123456789\n\n"
            "User ID ученика можно узнать когда он напишет боту — "
            "бот пришлёт тебе уведомление."
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат. Укажи числовой ID.")
        return

    await grant_access(target_id)
    await message.answer(f"✅ Доступ открыт для пользователя {target_id}.\nПервый урок придёт в ближайшее воскресенье.")

    # Уведомляем ученика
    try:
        await message.bot.send_message(
            target_id,
            "🎉 *Доступ к курсу открыт!*\n\n"
            "Добро пожаловать на курс Beauty Marketing!\n\n"
            "📅 Первый урок придёт в *воскресенье в 10:00 МСК*.\n"
            "До встречи! 👋",
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer("⚠️ Не удалось уведомить ученика (возможно, не писал боту).")


@router.message(Command("students"))
async def cmd_students(message: types.Message):
    """Список всех учеников для администратора."""
    if message.from_user.id != ADMIN_ID:
        return

    users = await get_all_users_for_admin()
    if not users:
        await message.answer("Пока нет зарегистрированных пользователей.")
        return

    lines = ["👥 *Список учеников:*\n"]
    for u in users:
        access = "✅" if u["has_access"] else "❌"
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lesson = u["current_lesson"] or 0
        hw = u["homework_status"] or "—"
        lines.append(f"{access} {name} | Урок {lesson} | ДЗ: {hw} | ID: {u['user_id']}")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("newuser"))
async def notify_admin_new_user(message: types.Message):
    """Ученик написал боту впервые — сообщаем администратору."""
    pass  # реализовано в middleware
