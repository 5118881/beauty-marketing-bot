from aiogram import Router, Bot, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID, TARIFFS, PAYMENT_QR_PATH, PAYMENT_SBP_LINK, payment_instructions, COURSE_TITLE
from db.database import register_user, has_access, get_progress, get_all_users_for_admin, grant_access, has_given_consent, set_selected_tariff
from lessons.content import total_lessons
from lessons.legal import CONSENT_TEXT

router = Router()

def _consent_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оферта", callback_data="show_offer")
    kb.button(text="Политика данных", callback_data="show_policy")
    kb.button(text="Принимаю", callback_data="consent_accept")
    kb.adjust(2, 1)
    return kb.as_markup()

def _tariff_keyboard():
    kb = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        kb.button(text=f"{t['name']} - {t['price']} руб.", callback_data=f"tariff_{key}")
    kb.adjust(1)
    return kb.as_markup()

def _payment_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить по СБП", url=PAYMENT_SBP_LINK)
    kb.button(text="Я оплатила", callback_data="i_paid")
    kb.button(text="Назад к тарифам", callback_data="back_to_tariffs")
    kb.adjust(1)
    return kb.as_markup()

async def send_main_menu(bot: Bot, user: types.User):
    if await has_access(user.id):
        progress = await get_progress(user.id)
        lesson = progress["current_lesson"]
        hw_status = progress["homework_status"]
        status_text = ""
        if hw_status == "waiting":
            status_text = "\n\nТвоё домашнее задание ожидает проверки."
        elif hw_status == "revision":
            status_text = "\n\nКуратор попросил доработать ДЗ."
        elif hw_status == "approved":
            status_text = "\n\nДЗ принято! Жди следующий урок."
        await bot.send_message(user.id, f"С возвращением, {user.first_name}!\n\nТекущий урок: {lesson} из {total_lessons()}{status_text}")
        return
    await bot.send_message(user.id, f"Привет, {user.first_name}!\n\nДобро пожаловать на курс {COURSE_TITLE}\n\nВыбери тариф:", reply_markup=_tariff_keyboard())

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name)
    if not await has_given_consent(user.id):
        await message.answer(CONSENT_TEXT, reply_markup=_consent_keyboard(), disable_web_page_preview=True)
        return
    await send_main_menu(message.bot, user)

@router.callback_query(F.data.startswith("tariff_"))
async def cb_select_tariff(callback: types.CallbackQuery):
    tariff_key = callback.data.split("_", 1)[1]
    if tariff_key not in TARIFFS:
        await callback.answer("Неизвестный тариф.")
        return
    tariff = TARIFFS[tariff_key]
    try:
        await callback.message.edit_text(tariff["description"])
    except Exception:
        pass
    await callback.message.answer_photo(FSInputFile(PAYMENT_QR_PATH), caption=payment_instructions(tariff_key), reply_markup=_payment_keyboard())
    await set_selected_tariff(callback.from_user.id, tariff_key)
    await callback.answer()

@router.callback_query(F.data == "back_to_tariffs")
async def cb_back_to_tariffs(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Выбери тариф:", reply_markup=_tariff_keyboard())
    await callback.answer()

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    if not await has_access(user_id):
        await message.answer("Нет доступа. Напиши /start чтобы выбрать тариф.")
        return
    progress = await get_progress(user_id)
    lesson = progress["current_lesson"]
    hw_status = progress["homework_status"]
    hw_map = {"none": "Жди следующего урока", "waiting": "ДЗ ожидает проверки", "revision": "Нужна доработка", "approved": "ДЗ принято!"}
    await message.answer(f"Прогресс:\n\nУрок: {lesson} из {total_lessons()}\nДЗ: {hw_map.get(hw_status, '-')}")

@router.message(Command("grant"))
async def cmd_grant(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /grant [user_id]")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Неверный ID.")
        return
    await grant_access(target_id)
    await message.answer(f"Доступ открыт для {target_id}.")
    from handlers.lessons import send_lesson_to_user
    await send_lesson_to_user(message.bot, target_id)

@router.message(Command("students"))
async def cmd_students(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = await get_all_users_for_admin()
    if not users:
        await message.answer("Пока нет пользователей.")
        return
    lines = ["Список учеников:\n"]
    for u in users:
        access = "+" if u["has_access"] else "-"
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"{access} {name} | Урок {u['current_lesson'] or 0} | ID: {u['user_id']}")
    await message.answer("\n".join(lines))
