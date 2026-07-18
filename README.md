# 🤖 Telegram-бот для онлайн-курса

Полноценный бот с уроками по расписанию, тестами и приёмом оплаты.

---

## 📁 Структура проекта

```
telegram_course_bot/
├── bot.py                  # Точка входа
├── config.py               # Настройки (токены, цена)
├── requirements.txt
├── db/
│   └── database.py         # База данных SQLite
├── handlers/
│   ├── start.py            # /start, /status
│   ├── payment.py          # Оплата через Telegram Payments
│   ├── lessons.py          # Отправка уроков
│   └── quiz.py             # Тесты после уроков
├── lessons/
│   └── content.py          # ВСЕ уроки и вопросы — редактируй здесь
└── utils/
    └── scheduler.py        # Автоматическая рассылка уроков
```

---

## 🚀 Быстрый старт

### 1. Получи токен бота
Открой [@BotFather](https://t.me/BotFather) в Telegram:
- `/newbot` — создать нового бота
- Скопируй токен

### 2. Подключи оплату (опционально)
В [@BotFather](https://t.me/BotFather):
- `/mybots` → твой бот → Payments
- Выбери провайдера (ЮКасса, Stripe и др.)
- Скопируй токен провайдера

### 3. Настрой config.py
```python
BOT_TOKEN = "123456:ABC-DEF..."          # токен от BotFather
ADMIN_ID = 123456789                      # твой Telegram ID (узнать у @userinfobot)
PAYMENT_PROVIDER_TOKEN = "381764628:..."  # токен платёжного провайдера
COURSE_PRICE = 1990                       # цена в рублях
```

### 4. Добавь уроки
Открой `lessons/content.py` и заполни список `LESSONS`:
```python
{
    "number": 1,
    "title": "Урок 1: Введение",
    "text": "Текст урока в Markdown...",
    "video_url": None,    # или file_id видео из Telegram
    "quiz": [
        {
            "question": "Вопрос?",
            "options": ["А", "Б", "В", "Г"],
            "correct": 0,   # индекс правильного ответа
        }
    ]
}
```

### 5. Установи зависимости и запусти
```bash
pip install -r requirements.txt
python bot.py
```

---

## ⚙️ Как это работает

| Функция | Описание |
|---|---|
| `/start` | Приветствие + кнопки "О курсе" и "Купить" |
| `/status` | Прогресс пользователя |
| **Оплата** | Через Telegram Payments (встроенная) |
| **Уроки** | Каждый день в 10:00 UTC автоматически |
| **Тесты** | После каждого урока, кнопками |

---

## 🌐 Деплой на сервер (VPS)

```bash
# На сервере Ubuntu/Debian
git clone ...
cd telegram_course_bot
pip install -r requirements.txt

# Запуск как сервис (systemd)
sudo nano /etc/systemd/system/coursebot.service
```

```ini
[Unit]
Description=Course Telegram Bot
After=network.target

[Service]
WorkingDirectory=/path/to/telegram_course_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable coursebot
sudo systemctl start coursebot
```

---

## 💡 Частые вопросы

**Как отправить урок вручную?**
Добавь команду `/sendlesson` в `handlers/start.py` с проверкой ADMIN_ID.

**Как добавить видео в урок?**
Сначала отправь видео боту, скопируй `file_id` из лога, вставь в `video_url`.

**Как изменить время рассылки?**
В `config.py`: `LESSON_SEND_HOUR` и `LESSON_SEND_MINUTE` (UTC).
