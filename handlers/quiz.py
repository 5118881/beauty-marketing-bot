from aiogram import Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import save_quiz_result
from lessons.content import get_lesson

router = Router()

# Временное хранилище ответов пользователя в памяти
# (для продакшена лучше FSM или Redis)
user_quiz_state: dict[int, dict] = {}


@router.callback_query(lambda c: c.data and c.data.startswith("quiz_"))
async def handle_quiz(callback: types.CallbackQuery):
    """
    Формат callback_data:
      quiz_{lesson_num}_{question_index}           — начать / следующий вопрос
      answer_{lesson_num}_{question_index}_{choice} — ответ пользователя
    """
    parts = callback.data.split("_")
    action = parts[0]

    if action == "quiz":
        lesson_num = int(parts[1])
        q_index = int(parts[2])
        await send_question(callback, lesson_num, q_index)

    elif action == "answer":
        lesson_num = int(parts[1])
        q_index = int(parts[2])
        chosen = int(parts[3])
        await process_answer(callback, lesson_num, q_index, chosen)

    await callback.answer()


async def send_question(callback: types.CallbackQuery, lesson_num: int, q_index: int):
    lesson = get_lesson(lesson_num)
    if not lesson:
        return

    quiz = lesson["quiz"]
    if q_index >= len(quiz):
        # Все вопросы отвечены — показываем результат
        await show_result(callback, lesson_num, lesson)
        return

    question = quiz[q_index]
    kb = InlineKeyboardBuilder()
    for i, option in enumerate(question["options"]):
        kb.button(
            text=option,
            callback_data=f"answer_{lesson_num}_{q_index}_{i}"
        )
    kb.adjust(1)

    await callback.message.edit_text(
        f"❓ *Вопрос {q_index + 1} из {len(quiz)}*\n\n"
        f"{question['question']}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


async def process_answer(
    callback: types.CallbackQuery,
    lesson_num: int,
    q_index: int,
    chosen: int
):
    lesson = get_lesson(lesson_num)
    if not lesson:
        return

    user_id = callback.from_user.id
    quiz = lesson["quiz"]
    question = quiz[q_index]
    is_correct = chosen == question["correct"]

    # Сохраняем ответ
    if user_id not in user_quiz_state:
        user_quiz_state[user_id] = {}
    key = f"{lesson_num}_{q_index}"
    user_quiz_state[user_id][key] = is_correct

    # Feedback
    correct_text = question["options"][question["correct"]]
    if is_correct:
        feedback = "✅ Правильно!"
    else:
        feedback = f"❌ Неверно. Правильный ответ: *{correct_text}*"

    await callback.message.answer(feedback, parse_mode="Markdown")

    # Переходим к следующему вопросу
    next_q = q_index + 1
    if next_q < len(quiz):
        kb = InlineKeyboardBuilder()
        kb.button(text="➡️ Следующий вопрос", callback_data=f"quiz_{lesson_num}_{next_q}")
        await callback.message.answer("Готов к следующему?", reply_markup=kb.as_markup())
    else:
        # Считаем результат
        score = sum(
            1 for k, v in user_quiz_state.get(user_id, {}).items()
            if k.startswith(f"{lesson_num}_") and v
        )
        total = len(quiz)
        await save_quiz_result(user_id, lesson_num, score, total)

        # Очищаем состояние
        if user_id in user_quiz_state:
            del user_quiz_state[user_id]

        percent = int(score / total * 100)
        emoji = "🏆" if percent >= 80 else "📊"
        await callback.message.answer(
            f"{emoji} *Результат теста:*\n\n"
            f"Правильных ответов: {score} из {total} ({percent}%)\n\n"
            f"{'Отличная работа! 🎉' if percent >= 80 else 'Не расстраивайся, продолжай учиться! 💪'}\n\n"
            f"Следующий урок придёт по расписанию.",
            parse_mode="Markdown"
        )


async def show_result(callback: types.CallbackQuery, lesson_num: int, lesson: dict):
    """Показываем итог если все вопросы уже отвечены."""
    await callback.message.answer("✅ Тест по этому уроку уже пройден! Жди следующий урок.")
