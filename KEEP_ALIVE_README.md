# 🏐 Volleyball Bot - Keep-Alive Solution

## Проблема
На бесплатном плане Render.com сервис "засыпает" после 15 минут бездействия, что приводит к задержкам в 50+ секунд при первом запросе.

## Решение
Реализована система keep-alive с несколькими компонентами:

### 1. Встроенный Self-Ping (основной)
В `bot.py` добавлен механизм самопинга каждые 10 минут:
- Endpoint `/ping` для проверки работоспособности
- Автоматический ping самого себя каждые 10 минут
- Работает асинхронно вместе с ботом

### 2. Мониторинг Endpoints
Добавлены endpoint'ы для мониторинга:
- `/health` - проверка работоспособности (JSON)
- `/status` - статус сервиса с timestamp
- `/ping` - простой ping ответ  
- `/monitor` - HTML страница мониторинга

### 3. Внешний Node.js скрипт (дополнительно)
`keep-alive.js` - может быть запущен на отдельном сервере или локально:
```bash
node keep-alive.js
```

### 4. HTML мониторинг
`monitor.html` - веб-интерфейс для мониторинга доступен по `/monitor`

## Развертывание

### 1. Обновите код на Render
```bash
git add .
git commit -m "Add keep-alive system"
git push origin main
```

### 2. Проверьте endpoints
После развертывания проверьте:
- https://volleyball-bot-last.onrender.com/health
- https://volleyball-bot-last.onrender.com/monitor

### 3. Тестирование локально
```bash
python test_endpoints.py
```

## Проверка работы

### В логах Render должно появиться:
```
🔄 Keep-alive ping sent successfully
🔄 Keep-alive ping sent successfully
```

### Мониторинг:
- Откройте https://volleyball-bot-last.onrender.com/monitor
- Страница должна показывать статус "Active" и время последней проверки

## Альтернативные решения

### 1. Внешние сервисы мониторинга:
- UptimeRobot (бесплатно до 50 мониторов)
- Pingdom
- StatusCake

### 2. Cron-job сервисы:
- cron-job.org
- EasyCron

### 3. GitHub Actions:
Можно настроить GitHub Action для пинга каждые 10 минут.

## Настройка внешнего мониторинга

### UptimeRobot:
1. Регистрируетесь на uptimerobot.com
2. Добавляете монитор типа "HTTP(s)"
3. URL: https://volleyball-bot-last.onrender.com/ping
4. Интервал: 5 минут

### GitHub Actions пример:
```yaml
name: Keep Alive
on:
  schedule:
    - cron: '*/10 * * * *'  # Каждые 10 минут
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping service
        run: curl https://volleyball-bot-last.onrender.com/ping
```

## Мониторинг эффективности

Следите за логами в Render Dashboard - если система работает правильно, сервис не должен "засыпать" и time to first response должно быть < 1 секунды вместо 50+ секунд.
