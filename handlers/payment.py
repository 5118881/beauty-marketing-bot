from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    PAYMENT_PROVIDER_TOKEN, COURSE_PRICE,
    COURSE_TITLE, COURSE_DESCRIPTION
)
from db.database import grant_access, has_access

router = Router()


@router.callback_query(lambda c: c.data == "buy")
async def send_invoice(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # Проверяем, не купил ли уже
    if await has_access(user_id):
        await callback.message.answer("✅ У тебя уже есть доступ к курсу! Уроки придут по расписанию.")
        await callback.answer()
        return

    await callback.message.answer_invoice(
        title=COURSE_TITLE,
        description=COURSE_DESCRIPTION,
        payload="course_payment",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[
            types.LabeledPrice(
                label=COURSE_TITLE,
                amount=COURSE_PRICE * 100   # в копейках
            )
        ],
        start_parameter="buy_course",
        photo_url=None,   # Можно вставить ссылку на обложку курса
        need_name=False,
        need_email=False,
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    """Telegram требует подтвердить оплату перед списанием."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: types.Message):
    """Обработка успешной оплаты."""
    user_id = message.from_user.id
    await grant_access(user_id)

    await message.answer(
        "🎉 *Оплата прошла успешно!*\n\n"
        "Добро пожаловать на курс!\n\n"
        "📚 Первый урок придёт сегодня по расписанию.\n"
        "Используй /status чтобы посмотреть свой прогресс.",
        parse_mode="Markdown"
    )
