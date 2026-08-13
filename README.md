# English Journey — Telegram Mini App

Telegram-бот и мини-приложение для взрослого изучения английского с нуля до A1 по CEFR.

## Возможности

- **Полный маршрут Pre-A1/A1** — 52 модуля и 156 занятий, включая Backend English
- **Упражнения** — выбор ответа, перевод, заполнение пропусков, произношение
- **Голосовой модуль** — TTS (gTTS) и STT (SpeechRecognition)
- **Spaced Repetition** — алгоритм SM-2 для повторения
- **Экзамены по уровням** — Pre-A1 и A1
- **Прогресс** — XP, навыки, streak (дни подряд)
- **Telegram Mini App** — красивый UI прямо в Telegram

## Быстрый старт

### 1. Установка

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка

```bash
cp .env.example .env
# Отредактируйте .env — добавьте TELEGRAM_BOT_TOKEN от @BotFather
```

### 3. База данных и контент

```bash
python manage.py migrate
python manage.py seed_content  # 156 lessons + speaking/writing missions + reading
python manage.py audit_curriculum
python manage.py createsuperuser  # опционально, для админки
```

### 4. Запуск

```bash
uvicorn config.asgi:application --reload --port 8000
```

Откройте http://localhost:8000/miniapp/ — мини-приложение.

### 5. Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. В BotFather: `/newapp` → привяжите Web App URL (`https://your-domain/miniapp/`)
3. Для локальной разработки используйте ngrok/cloudflared:

```bash
cloudflared tunnel --url http://localhost:8000
# или: ngrok http 8000
```

4. Обновите `.env`:
   - `TELEGRAM_BOT_TOKEN=...`
   - `TELEGRAM_WEBAPP_URL=https://your-tunnel/miniapp/`
   - `TELEGRAM_WEBHOOK_URL=https://your-tunnel/bot/webhook/`

5. Установите webhook:

```bash
python manage.py set_webhook https://your-tunnel/bot/webhook/
```

6. Напишите боту `/start` в Telegram!

### Polling (без webhook, для локальной отладки)

```bash
python manage.py run_bot
```

## Серверный Docker

```bash
docker compose up --build
```

## Структура проекта

```
english_bot/
├── config/           # Django settings, ASGI
├── apps/
│   ├── users/      # LearnerProfile, streak, XP
│   ├── learning/   # Lessons, exercises, SRS, exams, API
│   ├── voice/      # TTS/STT/pronunciation
│   └── bot/        # Telegram bot handlers
├── templates/miniapp/
├── static/miniapp/   # CSS + JS
└── manage.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard` | Статистика пользователя |
| GET | `/api/lessons` | Список уроков |
| GET | `/api/lessons/{id}` | Детали урока |
| GET | `/api/lessons/{id}/exercises` | Упражнения |
| POST | `/api/exercises/{id}/answer` | Ответ на упражнение |
| GET | `/api/reviews` | Карточки для повторения |
| GET | `/api/exam/{level}` | Экзамен |
| POST | `/api/exam/{level}/submit` | Сдача экзамена |
| GET | `/voice/tts/?text=hello` | TTS аудио |

## Speaking / Conversation

Вкладка **Speak** в мини-апп:

| Режим | Что делает |
|-------|------------|
| **Shadow** | Слушай (normal/slow) → повтори → оценка A+/A/B/C + tips |
| **Talk** | Ролевые диалоги (кафе, знакомство, магазин…) голосом |
| **Sounds** | Фонетика TH / W / V / гласные для русскоязычных |

Цель: **10 минут говорения в день** (отдельный прогресс-бар на Home).

Бот: `/speak` — фраза для повторения; голосовое сообщение → оценка произношения.

```bash
python manage.py seed_content
python manage.py audit_curriculum
```

На личном сервере STT использует Google SpeechRecognition без тяжёлого PyTorch.
Локальный Whisper можно установить отдельно только на машине с достаточным диском и RAM.


- `/start` — приветствие + кнопка мини-апп
- `/learn` — открыть обучение
- `/status` — прогресс и навыки
- `/streak` — серия дней
- `/help` — справка
- Голосовые сообщения — проверка произношения
- `say hello` — тренировка фразы

## Контент

`seed_content` создаёт полный маршрут Pre-A1/A1, разговорные миссии и оригинальные graded readers. Дополнительный импорт открытых книг и словаря запускается отдельно:

```bash
# Скачать книги с Project Gutenberg (локально в data/books/)
python manage.py download_books

# Импорт библиотеки книг; книги больше не создают бессмысленные автоуроки
python manage.py import_content

# Только graded stories (без сети)
python manage.py import_content --graded-only

# Без повторной загрузки словаря
python manage.py import_content --skip-vocabulary

# Частотный список с машинными/неполными переводами — только если он действительно нужен
python manage.py import_content --include-frequency-vocabulary
```

Основной курс содержит 30 последовательных занятий Pre-A1 и 90 занятий A1. Книги доступны отдельно в библиотеке и не смешиваются с учебным маршрутом. Методика и ограничения описаны в `CURRICULUM.md`.

### Дополнительные источники импорта

| Источник | Что даёт |
|----------|----------|
| Project Gutenberg | Alice in Wonderland, Wizard of Oz, Grimms' Fairy Tales, Frankenstein, Tom Sawyer, Sherlock Holmes и др. |
| Google 10K English | Частотный словарь 3000+ слов |
| Curated translations | ~660 слов с переводом EN→RU |
| Graded stories | 5 адаптированных историй (A1–B1) |

Основной seed: 42 урока Pre-A1, 114 уроков A1, 52 многоходовые разговорные
миссии, 312 фраз, 52 письменных задания, 18 оригинальных материалов для чтения
и два четырёхкомпонентных экзамена.

## Технологии

- Django 5 + ASGI (uvicorn)
- django-ninja (REST API)
- python-telegram-bot 21
- gTTS + SpeechRecognition (голос)
- SM-2 spaced repetition
- Telegram Web App SDK

## Лицензия

MIT
