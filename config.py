# config.py — настройки бота
BOT_TOKEN = "7244985970:AAHfGqI8JTHI-04qf8eSl4ZruHnfRFSfkXU"

ADMIN_ID = 161746727                    # Dasha_Ras4eshi

COURSE_TITLE = "Beauty Marketing — полный курс"
COURSE_DESCRIPTION = "Онлайн-курс по маркетингу в бьюти-индустрии"

# База данных
DATABASE_PATH = "course.db"

# Расписание: каждое воскресенье в 10:00 МСК (07:00 UTC)
LESSON_DAY_OF_WEEK = "sun"   # mon, tue, wed, thu, fri, sat, sun
LESSON_SEND_HOUR = 7         # UTC (7 = 10:00 МСК)
LESSON_SEND_MINUTE = 0

# Оплата (опционально — заполни если хочешь принимать платежи через Telegram)
PAYMENT_PROVIDER_TOKEN = ""   # получить у @BotFather → /mybots → Payments
COURSE_PRICE = 1990           # цена в рублях
