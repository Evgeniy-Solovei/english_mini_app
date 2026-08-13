# Локальный запуск с PostgreSQL

Приложение использует PostgreSQL и локально, и на сервере. SQLite используется только как одноразовая in-memory база тестов.

## Локальная база без Docker

```bash
createdb english_bot
cp .env.example .env
# В .env: DB_HOST=localhost и данные вашего локального PostgreSQL
python manage.py migrate
python manage.py load_initial_content
```

Mini App: `http://127.0.0.1:8001/miniapp/`.

## Запуск Django без контейнера

Приложение запускается с хоста командой `uvicorn config.asgi:application --reload`.
Docker для локальной разработки не нужен; compose-файлы предназначены только для сервера.

## Telegram через временный HTTPS

```bash
ngrok http 8000
python manage.py set_webhook https://ВАШ-ДОМЕН.ngrok-free.app/bot/webhook/
```

В `.env` обновите `TELEGRAM_WEBHOOK_URL` и `TELEGRAM_WEBAPP_URL`. Никогда не записывайте настоящий токен бота в документацию или git.

## Проверки

```bash
python manage.py test
docker compose ps
docker compose logs --tail=100 web db
```
