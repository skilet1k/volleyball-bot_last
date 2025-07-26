# Volleyball Bot

Telegram бот для записи на игры в волейбол в Варшаве.

## Развертывание на Render.com

1. Создайте аккаунт на [render.com](https://render.com)
2. Загрузите код на GitHub
3. Создайте PostgreSQL базу данных на Render
4. Создайте веб-сервис и настройте переменные окружения

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` - токен вашего бота от @BotFather
- `POSTGRES_DSN` - строка подключения к PostgreSQL базе данных

## Локальная разработка

```bash
python -m venv .venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```
