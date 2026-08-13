# Развёртывание на english-bot.live-dev.by

## 1. Настройка

```bash
cp .env.example .env
```

В `.env` обязательно замените `SECRET_KEY`, `POSTGRES_PASSWORD`, `TELEGRAM_BOT_TOKEN` и `TELEGRAM_WEBHOOK_SECRET`. Значения домена уже указаны для `https://english-bot.live-dev.by`.

Для neural TTS с разными голосами и фонемной проверки произношения также задайте
`AZURE_SPEECH_KEY` и `AZURE_SPEECH_REGION`. Без них приложение работает через
gTTS/Whisper, но показывает только приближённую оценку по распознанному тексту.

## 2. Запуск

```bash
docker compose up -d --build
```

Контейнер `web` ждёт healthcheck PostgreSQL, применяет миграции и при пустой базе автоматически загружает подготовленный учебный fixture. PostgreSQL хранит данные в постоянном volume `pg_data`; наружу порт 5432 не публикуется.

## 3. Загрузка подготовленного контента

Подготовленный fixture загружается непосредственно в PostgreSQL. Пользовательские профили и история в него не входят.

Ручная команда нужна только если вы установили `LOAD_INITIAL_DATA=0`:

```bash
docker compose exec web python manage.py load_initial_content
```

Если база уже содержит старый учебный контент, сначала сохраните её резервную копию, затем выполните:

```bash
docker compose exec web python manage.py seed_content
docker compose exec web python manage.py audit_curriculum
```

`seed_content` заменяет учебные уроки, экзамены, словарь и разговорные сценарии.
Профили и учётные записи не удаляются, но прогресс по заменённым урокам будет
сброшен. Перед обновлением обязательно сделайте `pg_dump`.

## 4. Telegram webhook

```bash
docker compose exec web python manage.py set_webhook https://english-bot.live-dev.by/bot/webhook/
```

Проверка приложения:

```bash
curl -I https://english-bot.live-dev.by/miniapp/
docker compose logs --tail=100 web
```

В BotFather URL Mini App должен быть `https://english-bot.live-dev.by/miniapp/`.

## Резервная копия PostgreSQL

```bash
docker compose exec -T db pg_dump -U english_bot -d english_bot -Fc > english_bot_postgres.dump
```

Восстановление в пустую базу:

```bash
docker compose exec -T db pg_restore -U english_bot -d english_bot --clean --if-exists < english_bot_postgres.dump
```

## Обновление дампа

```bash
python manage.py dumpdata \
  learning.Lesson learning.Exercise learning.Word learning.LevelExam learning.ReadingText \
  learning.PhrasePack learning.ShadowPhrase learning.DialogueScenario \
  --indent 2 --output dumps/english_bot_curriculum_v3_2026-08-12.json.gz
```
