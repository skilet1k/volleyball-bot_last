# Volleyball Bot

Telegram бот для записи на игры в волейбол в Варшаве.

## Развертывание на Render.com

### Шаг 1: Создайте PostgreSQL базу данных

1. Зайдите на [render.com](https://render.com) и войдите в аккаунт
2. Нажмите "New +" → "PostgreSQL"
3. Заполните форму:
   - **Name**: `volleyball-bot-db`
   - **Database**: `volleyball`
   - **User**: `volleyball_user`
   - **Region**: Frankfurt (EU Central)
   - **Plan**: Free
4. Нажмите "Create Database"
5. **ВАЖНО**: Скопируйте "External Database URL" - это ваш `POSTGRES_DSN`

### Шаг 2: Создайте Web Service

1. Нажмите "New +" → "Web Service"
2. Выберите "Public Git repository"
3. Вставьте URL: `https://github.com/YOUR_USERNAME/volleyball-bot.git`
4. Заполните настройки:
   - **Name**: `volleyball-bot`
   - **Environment**: `Python 3`
   - **Region**: Frankfurt (EU Central)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

### Шаг 3: Настройте переменные окружения

В разделе "Environment Variables" добавьте:

1. **TELEGRAM_BOT_TOKEN**:
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: `7552454167:AAGJCiF2yiQ-oMokKORBHosgdAHzgLei74U`

2. **POSTGRES_DSN**:
   - Key: `POSTGRES_DSN`
   - Value: (URL из шага 1, например: `postgresql://user:password@host:port/database`)

### Шаг 4: Деплой

1. Нажмите "Create Web Service"
2. Дождитесь завершения сборки (5-10 минут)
3. Проверьте логи в разделе "Logs"

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` - токен вашего бота от @BotFather
- `POSTGRES_DSN` - строка подключения к PostgreSQL базе данных

## Создание репозитория на GitHub

1. Зайдите на https://github.com/new
2. Название: `volleyball-bot`
3. Сделайте репозиторий **публичным**
4. НЕ добавляйте README, .gitignore или лицензию
5. Загрузите все файлы из этой папки в новый репозиторий

## Локальная разработка

```bash
python -m venv .venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```
