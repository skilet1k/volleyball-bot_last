import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
import asyncpg
import datetime

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    TOKEN = "7552454167:AAGJCiF2yiQ-oMokKORBHosgdAHzgLei74U"  # <-- замените на свой токен

ADMIN_IDS = [760746564, 683243528, 1202044081]
DB_DSN = os.getenv('POSTGRES_DSN') or 'postgresql://postgres:postgres@localhost:5432/volleyball'

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_states = {}
add_game_states = {}
# PostgreSQL pool helper
_pg_pool = None
async def get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(dsn=DB_DSN)
    return _pg_pool

LANGUAGES = {
    'ru': 'Русский',
    'uk': 'Українська',
    'en': 'English'
}

TEXTS = {
    'welcome': {
        'ru': "Добро пожаловать! Выберите язык:",
        'uk': "Ласкаво просимо! Виберіть мову:",
        'en': "Welcome! Choose your language:"
    },
    'choose_action': {
        'ru': "Выберите действие:",
        'uk': "Виберіть дію:",
        'en': "Choose an action:"
    },
    'schedule_empty': {
        'ru': "Расписание пусто.",
        'uk': "Розклад порожній.",
        'en': "Schedule is empty."
    },
    'my_records_empty': {
        'ru': "Вы пока не записали ни одного человека.",
        'uk': "Ви ще нікого не записали.",
        'en': "You haven't registered anyone yet."
    },
    'enter_name': {
        'ru': "Введите имя и фамилию для записи:",
        'uk': "Введіть ім'я та прізвище для запису:",
        'en': "Enter name and surname for registration:"
    },
    'enter_username': {
        'ru': "Введите ваш ник в Telegram (например, @nickname):",
        'uk': "Введіть ваш нік в Telegram (наприклад, @nickname):",
        'en': "Enter your Telegram username (e.g., @nickname):"
    },
    'registered': {
        'ru': "Записано!",
        'uk': "Записано!",
        'en': "Registered!"
    },
    'no_access': {
        'ru': "Нет доступа.",
        'uk': "Немає доступу.",
        'en': "No access."
    },
    'add_game_date': {
        'ru': "Введите дату игры (например, 21.07.2025):",
        'uk': "Введіть дату гри (наприклад, 21.07.2025):",
        'en': "Enter game date (e.g., 21.07.2025):"
    },
    'add_game_time_start': {
        'ru': "Введите время начала (например, 18:00):",
        'uk': "Введіть час початку (наприклад, 18:00):",
        'en': "Enter start time (e.g., 18:00):"
    },
    'add_game_time_end': {
        'ru': "Введите время окончания (например, 20:00):",
        'uk': "Введіть час закінчення (наприклад, 20:00):",
        'en': "Enter end time (e.g., 20:00):"
    },
    'add_game_place': {
        'ru': "Введите место:",
        'uk': "Введіть місце:",
        'en': "Enter place:"
    },
    'add_game_price': {
        'ru': "Введите цену (PLN):",
        'uk': "Введіть ціну (PLN):",
        'en': "Enter price (PLN):"
    },
    'add_game_added': {
        'ru': "Игра добавлена!",
        'uk': "Гру додано!",
        'en': "Game added!"
    },
    'add_game_price_error': {
        'ru': "Введите число!",
        'uk': "Введіть число!",
        'en': "Enter a number!"
    },
    'delete_game_empty': {
        'ru': "Нет игр для удаления.",
        'uk': "Немає ігор для видалення.",
        'en': "No games to delete."
    },
    'delete_game_choose': {
        'ru': "Выберите игру для удаления:",
        'uk': "Виберіть гру для видалення:",
        'en': "Choose a game to delete:"
    },
    'delete_game_done': {
        'ru': "Игра удалена.",
        'uk': "Гру видалено.",
        'en': "Game deleted."
    },
    'unknown_command': {
        'ru': "Неизвестная команда. Пожалуйста, выберите действие:",
        'uk': "Невідома команда. Будь ласка, виберіть дію:",
        'en': "Unknown command. Please choose an action:"
    },
    'record_deleted': {
        'ru': "Запись отменена.",
        'uk': "Запис скасовано.",
        'en': "Registration cancelled."
    },
    'record_not_found': {
        'ru': "Запись не найдена.",
        'uk': "Запис не знайдено.",
        'en': "Registration not found."
    },
    'paid_status_changed': {
        'ru': "Статус оплаты изменён на",
        'uk': "Статус оплати змінено на",
        'en': "Payment status changed to"
    }
}

def get_lang(user_id):
    return user_states.get(user_id, {}).get('lang', 'ru')

def reply_menu(is_admin=False, lang='ru'):
    buttons = [
        [KeyboardButton(text={'ru':'📅 Расписание','uk':'📅 Розклад','en':'📅 Schedule'}[lang])],
        [KeyboardButton(text={'ru':'🎟 Мои записи','uk':'🎟 Мої записи','en':'🎟 My records'}[lang])],
        [KeyboardButton(text={'ru':'⚙️ Параметры','uk':'⚙️ Параметри','en':'⚙️ Parameters'}[lang])]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text={'ru':'➕ Добавить игру','uk':'➕ Додати гру','en':'➕ Add game'}[lang])])
        buttons.append([KeyboardButton(text={'ru':'❌ Удалить игру','uk':'❌ Видалити гру','en':'❌ Delete game'}[lang])])
        buttons.append([KeyboardButton(text={'ru':'👥 Просмотреть записи','uk':'👥 Переглянути записи','en':'👥 View registrations'}[lang])])
        buttons.append([KeyboardButton(text={'ru':'📝 Создать пост','uk':'📝 Створити пост','en':'📝 Create post'}[lang])])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def init_db():
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            date TEXT,
            time_start TEXT,
            time_end TEXT,
            place TEXT,
            price INTEGER
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id SERIAL PRIMARY KEY,
            game_id INTEGER,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            paid INTEGER DEFAULT 0
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )''')

@dp.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES['ru'], callback_data='lang_ru')],
        [InlineKeyboardButton(text=LANGUAGES['uk'], callback_data='lang_uk')],
        [InlineKeyboardButton(text=LANGUAGES['en'], callback_data='lang_en')]
    ])
    user_states[message.from_user.id] = {}
    # Сохраняем пользователя при /start
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id, lang) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING', message.from_user.id, 'ru')
    await message.answer(TEXTS['welcome']['uk'], reply_markup=kb)

@dp.message(F.text.in_([
    '⚙️ Параметры', '⚙️ Параметри', '⚙️ Parameters'
]))
async def parameters_menu(message: Message):
    lang = get_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES['ru'], callback_data='lang_ru')],
        [InlineKeyboardButton(text=LANGUAGES['uk'], callback_data='lang_uk')],
        [InlineKeyboardButton(text=LANGUAGES['en'], callback_data='lang_en')],
        [InlineKeyboardButton(text={
            'ru': 'Наши ресурсы',
            'uk': 'Наші ресурси',
            'en': 'Our resources'
        }[lang], url='https://linktr.ee/volleyball_warsaw')],
        [InlineKeyboardButton(text={
            'ru': 'Написать админу',
            'uk': 'Написати адміну',
            'en': 'Contact admin'
        }[lang], url='https://t.me/hannazoria')],
        [InlineKeyboardButton(text={
            'ru': 'Чат по волейболу',
            'uk': 'Чат з волейболу',
            'en': 'Volleyball chat'
        }[lang], url='https://t.me/volleyball_warsaw')]
    ])
    await message.answer({'ru':'Выберите язык или ресурс:','uk':'Виберіть мову або ресурс:','en':'Choose language or resource:'}[lang], reply_markup=kb)

@dp.callback_query(F.data.startswith('lang_'))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split('_')[1]
    user_states[callback.from_user.id] = {'lang': lang}
    is_admin = callback.from_user.id in ADMIN_IDS
    # Сохраняем пользователя
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id, lang) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING', callback.from_user.id, lang)
    await callback.message.answer({'ru':'Язык изменён.','uk':'Мову змінено.','en':'Language changed.'}[lang], reply_markup=reply_menu(is_admin, lang))
    await callback.answer()

@dp.message(F.text.in_([
    '📅 Расписание', '📅 Розклад', '📅 Schedule'
]))
async def show_schedule(message: Message):
    lang = get_lang(message.from_user.id)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place, price FROM games')
        if not games:
            await message.answer(TEXTS['schedule_empty'][lang])
            return

        for game in games:
            game_id, date, time_start, time_end, place, price = game['id'], game['date'], game['time_start'], game['time_end'], game['place'], game['price']
            # Определяем день недели
            try:
                day, month, year = map(int, date.split('.'))
                dt = datetime.date(year, month, day)
                weekday = dt.strftime('%A')
                weekday_ru = {
                    'Monday': 'Понедельник',
                    'Tuesday': 'Вторник',
                    'Wednesday': 'Среда',
                    'Thursday': 'Четверг',
                    'Friday': 'Пятница',
                    'Saturday': 'Суббота',
                    'Sunday': 'Воскресенье'
                }
                weekday_uk = {
                    'Monday': 'Понеділок',
                    'Tuesday': 'Вівторок',
                    'Wednesday': 'Середа',
                    'Thursday': 'Четвер',
                    'Friday': 'Пʼятниця',
                    'Saturday': 'Субота',
                    'Sunday': 'Неділя'
                }
                weekday_en = {
                    'Monday': 'Monday',
                    'Tuesday': 'Tuesday',
                    'Wednesday': 'Wednesday',
                    'Thursday': 'Thursday',
                    'Friday': 'Friday',
                    'Saturday': 'Saturday',
                    'Sunday': 'Sunday'
                }
                weekday_short_ru = {
                    'Monday': 'пн',
                    'Tuesday': 'вт',
                    'Wednesday': 'ср',
                    'Thursday': 'чт',
                    'Friday': 'пт',
                    'Saturday': 'сб',
                    'Sunday': 'вс'
                }
                weekday_short_uk = {
                    'Monday': 'пн',
                    'Tuesday': 'вт',
                    'Wednesday': 'ср',
                    'Thursday': 'чт',
                    'Friday': 'пт',
                    'Saturday': 'сб',
                    'Sunday': 'нд'
                }
                weekday_short_en = {
                    'Monday': 'Mon',
                    'Tuesday': 'Tue',
                    'Wednesday': 'Wed',
                    'Thursday': 'Thu',
                    'Friday': 'Fri',
                    'Saturday': 'Sat',
                    'Sunday': 'Sun'
                }
                weekday_short_map = {'ru': weekday_short_ru, 'uk': weekday_short_uk, 'en': weekday_short_en}
                weekday_str = weekday_short_map.get(lang, weekday_short_en).get(weekday)
                if not weekday_str:
                    weekday_str = weekday_short_en.get(weekday, weekday)
            except Exception:
                weekday_str = ''  # fallback: show nothing if parsing fails
            registrations = await conn.fetch('SELECT full_name, username, paid FROM registrations WHERE game_id = $1 ORDER BY id', game_id)
            main_list = registrations[:14]
            reserve_list = registrations[14:]
            # Формируем ссылку на Google Maps
            maps_url = f'https://www.google.com/maps/search/?api=1&query={place.replace(" ", "+")}'
            place_link = f'<a href="{maps_url}">{place}</a>'
            # Если личные сообщения, делаем имя ссылкой на адрес, а username — на личку
            is_private = message.chat.type == 'private' if hasattr(message.chat, 'type') else getattr(message.chat, 'type', None) == 'private'
            def name_link(name, username):
                if username:
                    return f'<a href="https://t.me/{username.lstrip("@").strip()}">{name}</a>'
                return name
            reg_text = ""
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {name_link(r['full_name'], r['username'])} {'✅' if r['paid'] else ''}\n"
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {name_link(r['full_name'], r['username'])} {'✅' if r['paid'] else ''}\n"
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
            text = (f"📅 {date} ({weekday_str})\n"
                    f"⏰ {time_start} - {time_end}\n"
                    f"🏟️ {place_link}\n"
                    f"💵 {price} PLN\n"
                    f"{ {'ru':'Записались:','uk':'Записались:','en':'Registered:'}[lang] }\n{reg_text}")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text={'ru':'Записаться','uk':'Записатися','en':'Register'}[lang], callback_data=f'register_{game_id}')],
            ])
            await message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
@dp.callback_query(F.data.startswith('delreg_'))
async def delreg(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    game_id = int(callback.data.split('_')[1])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM registrations WHERE game_id = $1 AND user_id = $2', game_id, callback.from_user.id)
    await callback.message.answer({'ru':'Ваша запись удалена.','uk':'Вашу запис видалено.','en':'Your registration has been deleted.'}[lang], reply_markup=reply_menu(callback.from_user.id in ADMIN_IDS, lang=lang))

@dp.callback_query(F.data.startswith('register_'))
async def register(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    game_id = int(callback.data.split('_')[1])
    if callback.from_user.id not in user_states:
        user_states[callback.from_user.id] = {'lang': lang}
    user_states[callback.from_user.id]['registering'] = game_id

    # Получаем ранее записанных игроков ТОЛЬКО этого пользователя
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        previous = await conn.fetch('SELECT full_name, username FROM registrations WHERE user_id = $1', callback.from_user.id)

    if previous:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text={'ru':'Выбрать из ранее записанных','uk':'Вибрати з раніше записаних','en':'Choose from previous'}[lang], callback_data='choose_prev')],
            [InlineKeyboardButton(text={'ru':'Добавить нового','uk':'Додати нового','en':'Add new'}[lang], callback_data='add_new')]
        ])
        user_states[callback.from_user.id]['previous'] = previous
        await callback.message.answer({'ru':'Выберите действие:','uk':'Виберіть дію:','en':'Choose action:'}[lang], reply_markup=kb)
    else:
        user_states[callback.from_user.id]['step'] = 'name'
        await callback.message.answer(TEXTS['enter_name'][lang])

@dp.callback_query(F.data == 'choose_prev')
async def choose_prev(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    previous = user_states[callback.from_user.id].get('previous', [])
    seen = set()
    unique_previous = []
    for name, username in previous:
        key = (name.strip(), (username or '').strip())
        if key not in seen:
            seen.add(key)
            unique_previous.append((name, username))
    await delete_last_bot_message(callback.from_user.id, callback.message.chat)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{name}', callback_data=f'prev_{name}_{username}') for name, username in unique_previous]
    ])
    msg = await callback.message.answer({'ru':'Выберите игрока:','uk':'Виберіть гравця:','en':'Choose player:'}[lang], reply_markup=kb)
    user_states[callback.from_user.id]['last_bot_msg_id'] = msg.message_id

@dp.callback_query(F.data.startswith('prev_'))
async def prev_selected(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    parts = callback.data.split('_', 2)
    full_name = parts[1]
    username = parts[2]
    game_id = user_states[callback.from_user.id]['registering']
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES ($1, $2, $3, $4, $5)',
                           game_id, callback.from_user.id, username, full_name, 0)
    await delete_last_bot_message(callback.from_user.id, callback.message.chat)
    msg = await callback.message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(callback.from_user.id in ADMIN_IDS, lang=lang))
    user_states[callback.from_user.id]['last_bot_msg_id'] = msg.message_id
    user_states[callback.from_user.id].pop('registering', None)
    user_states[callback.from_user.id].pop('previous', None)

@dp.callback_query(F.data == 'add_new')
async def add_new(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    user_states[callback.from_user.id]['step'] = 'name'
    await callback.message.answer(TEXTS['enter_name'][lang])

@dp.message(F.text.in_([
    '➕ Добавить игру', '➕ Додати гру', '➕ Add game'
]))
async def add_game_menu(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(TEXTS['no_access'][lang])
        return
    add_game_states[message.from_user.id] = {'step': 'date'}
    await message.answer(TEXTS['add_game_date'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text={'ru':'Отмена','uk':'Скасувати','en':'Cancel'}[lang], callback_data='cancel_addgame')]]))

@dp.callback_query(F.data == 'cancel_addgame')
async def cancel_addgame(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    add_game_states.pop(callback.from_user.id, None)
    await callback.message.answer({'ru':'Создание игры отменено.','uk':'Створення гри скасовано.','en':'Game creation cancelled.'}[lang], reply_markup=reply_menu(callback.from_user.id in ADMIN_IDS, lang=lang))

@dp.message(F.text.in_([
    '🎟 Мои записи', '🎟 Мої записи', '🎟 My records'
]))
async def my_records(message: Message):
    lang = get_lang(message.from_user.id)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('''SELECT g.id, g.date, g.time_start, g.time_end, g.place, g.price FROM games g JOIN registrations r ON r.game_id = g.id WHERE r.user_id = $1 GROUP BY g.id ORDER BY g.date, g.time_start''', message.from_user.id)
        if not games:
            await message.answer(TEXTS['my_records_empty'][lang])
            return
        for game in games:
            game_id, date, time_start, time_end, place, price = game['id'], game['date'], game['time_start'], game['time_end'], game['place'], game['price']
            regs = await conn.fetch('SELECT id, full_name, paid FROM registrations WHERE game_id = $1 AND user_id = $2 ORDER BY id', game_id, message.from_user.id)
            maps_url = f'https://www.google.com/maps/search/?api=1&query={place.replace(" ", "+")}'
            place_link = f'<a href="{maps_url}">{place}</a>'
            reg_text = ''
            for idx, r in enumerate(regs, 1):
                reg_text += f"{idx}. {r['full_name']} {'✅' if r['paid'] else '❌'}\n"
            text = (f"📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place_link} 💵 {price} PLN\n"
                    f"{reg_text}")
            if len(regs) > 1:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text={'ru':f"Удалить: {r['full_name']}", 'uk':f"Видалити: {r['full_name']}", 'en':f"Delete: {r['full_name']}"}[lang], callback_data=f"delmyreg_{r['id']}") for r in regs]
                ])
                await message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
            elif len(regs) == 1:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text={'ru':'Удалить мою запись','uk':'Видалити мій запис','en':'Delete my registration'}[lang], callback_data=f"delmyreg_{regs[0]['id']}")]
                ])
                await message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
            else:
                await message.answer(text, parse_mode='HTML', disable_web_page_preview=True)
@dp.callback_query(F.data.startswith('delmyreg_'))
async def delmyreg(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    reg_id = int(callback.data.split('_')[1])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM registrations WHERE id = $1 AND user_id = $2', reg_id, callback.from_user.id)
    await callback.message.answer({'ru':'Ваша запись удалена.','uk':'Вашу запис видалено.','en':'Your registration has been deleted.'}[lang], reply_markup=reply_menu(callback.from_user.id in ADMIN_IDS, lang=lang))

@dp.callback_query(F.data.startswith('delgame_'))
async def delgame(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer(TEXTS['no_access'][lang])
        return
    game_id = int(callback.data.split('_')[1])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM games WHERE id = $1', game_id)
        await conn.execute('DELETE FROM registrations WHERE game_id = $1', game_id)
    await callback.message.answer(TEXTS['delete_game_done'][lang], reply_markup=reply_menu(True, lang))

@dp.message(F.text.in_([
    '👥 Просмотреть записи', '👥 Переглянути записи', '👥 View registrations'
]))
async def view_records(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(TEXTS['no_access'][lang])
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text={'ru':'Изменить расписание','uk':'Змінити розклад','en':'Edit schedule'}[lang], callback_data='edit_schedule_mode'),
            InlineKeyboardButton(text={'ru':'Удалить игрока','uk':'Видалити гравця','en':'Delete player'}[lang], callback_data='delete_player_mode')
        ]
    ])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place FROM games')
        if not games:
            await message.answer({'ru':'Нет доступных игр.','uk':'Немає доступних ігор.','en':'No available games.'}[lang])
            return
        for game in games:
            game_id, date, time_start, time_end, place = game['id'], game['date'], game['time_start'], game['time_end'], game['place']
            registrations = await conn.fetch('SELECT id, full_name, paid FROM registrations WHERE game_id = $1 ORDER BY id', game_id)
            main_list = registrations[:14]
            reserve_list = registrations[14:]
            reg_text = ""
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {r['full_name']} {'✅' if r['paid'] else ''} | /togglepaid_{r['id']}\n"
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {r['full_name']} {'✅' if r['paid'] else ''} | /togglepaid_{r['id']}\n"
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
            await message.answer(f"{ {'ru':'Игра','uk':'Гра','en':'Game'}[lang] } 📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place}\n{reg_text}", reply_markup=kb)

@dp.callback_query(F.data == 'edit_schedule_mode')
async def edit_schedule_mode(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer(TEXTS['no_access'][lang])
        return
    # Предлагаем выбрать игру для редактирования
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place FROM games')
        if not games:
            await callback.message.answer({'ru':'Нет доступных игр.','uk':'Немає доступних ігор.','en':'No available games.'}[lang])
            return
        kb_rows = []
        for game in games:
            game_id, date, time_start, time_end, place = game['id'], game['date'], game['time_start'], game['time_end'], game['place']
            kb_rows.append([InlineKeyboardButton(text=f"{date} {time_start}-{time_end} {place}", callback_data=f'editgame_{game_id}')])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await callback.message.answer('Выберите игру для редактирования:', reply_markup=kb)

@dp.callback_query(F.data.startswith('editgame_'))
async def editgame(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer(TEXTS['no_access'][lang])
        return
    game_id = int(callback.data.split('_')[1])
    if callback.from_user.id not in user_states:
        user_states[callback.from_user.id] = {'lang': lang}
    user_states[callback.from_user.id]['edit_game_id'] = game_id
    # Get current game info
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        game = await conn.fetchrow('SELECT date, time_start, time_end, place, price FROM games WHERE id = $1', game_id)
    if game:
        date, time_start, time_end, place, price = game['date'], game['time_start'], game['time_end'], game['place'], game['price']
        current_text = (
            {'ru':"Текущее расписание:", 'uk':"Поточний розклад:", 'en':"Current schedule:"}[lang] + "\n"
            + {'ru':f"Дата: {date}\nВремя начала: {time_start}\nВремя окончания: {time_end}\nМесто: {place}\nЦена: {price} PLN\n\nВведите новое расписание в формате:\nДата\nВремя начала\nВремя окончания\nМесто\nЦена",
                'uk':f"Дата: {date}\nЧас початку: {time_start}\nЧас закінчення: {time_end}\nМісце: {place}\nЦіна: {price} PLN\n\nВведіть новий розклад у форматі:\nДата\nЧас початку\nЧас закінчення\nМісце\nЦіна",
                'en':f"Date: {date}\nStart time: {time_start}\nEnd time: {time_end}\nPlace: {place}\nPrice: {price} PLN\n\nEnter new schedule in format:\nDate\nStart time\nEnd time\nPlace\nPrice"}[lang]
        )
        await callback.message.answer(current_text)
    else:
        await callback.message.answer({'ru':'Игра не найдена.','uk':'Гру не знайдено.','en':'Game not found.'}[lang])

@dp.message()
async def handle_messages(message: Message):
    lang = get_lang(message.from_user.id)
    # Сохраняем пользователя
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id, lang) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING', message.from_user.id, lang)
    # Сброс всех пользовательских состояний при нажатии кнопки главного меню
    main_menu_texts = [
        '📅 Расписание', '📅 Розклад', '📅 Schedule',
        '🎟 Мои записи', '🎟 Мої записи', '🎟 My records',
        '⚙️ Параметры', '⚙️ Параметри', '⚙️ Parameters',
        '➕ Добавить игру', '➕ Додати гру', '➕ Add game',
        '❌ Удалить игру', '❌ Видалити гру', '❌ Delete game',
        '👥 Просмотреть записи', '👥 Переглянути записи', '👥 View registrations',
        '📝 Создать пост', '📝 Створити пост', '📝 Create post'
    ]
    if message.text in main_menu_texts:
        user_states[message.from_user.id] = {'lang': lang}
        # Исправление: если выбрана '❌ Удалить игру', показать список игр для удаления
        if message.text in ['❌ Удалить игру', '❌ Видалити гру', '❌ Delete game']:
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                games = await conn.fetch('SELECT id, date, time_start, time_end, place FROM games')
            if not games:
                await message.answer(TEXTS['delete_game_empty'][lang])
                return
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{game['date']} {game['time_start']}-{game['time_end']} {game['place']}", callback_data=f"delgame_{game['id']}")]
                for game in games
            ])
            await message.answer(TEXTS['delete_game_choose'][lang], reply_markup=kb)
            return
    main_menu_texts = [
        '📅 Расписание', '📅 Розклад', '📅 Schedule',
        '🎟 Мои записи', '🎟 Мої записи', '🎟 My records',
        '⚙️ Параметры', '⚙️ Параметри', '⚙️ Parameters',
        '➕ Добавить игру', '➕ Додати гру', '➕ Add game',
        '❌ Удалить игру', '❌ Видалити гру', '❌ Delete game',
        '👥 Просмотреть записи', '👥 Переглянути записи', '👥 View registrations',
        '📝 Создать пост', '📝 Створити пост', '📝 Create post'
    ]
    if message.text in main_menu_texts:
        user_states[message.from_user.id] = {'lang': lang}
    # --- Создать пост ---
    if message.text in ['📝 Создать пост', '📝 Створити пост', '📝 Create post']:
        await create_post_start(message)
        return
    if user_states.get(message.from_user.id, {}).get('create_post'):
        user_states[message.from_user.id]['post_text'] = message.text
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Добавить кнопку "Расписание"', callback_data='add_schedule_btn')],
            [InlineKeyboardButton(text='Без кнопки', callback_data='no_btn')]
        ])
        await message.answer('Добавить кнопку к посту?', reply_markup=kb)
        return

    # Добавление игры с кнопкой "Отмена"
    if message.from_user.id in add_game_states:
        state = add_game_states[message.from_user.id]
        step = state['step']
        if message.text == 'Отмена':
            add_game_states.pop(message.from_user.id, None)
            await message.answer('Создание игры отменено.', reply_markup=reply_menu(message.from_user.id in ADMIN_IDS, lang=lang))
            return
        if step == 'date':
            state['date'] = message.text.strip()
            state['step'] = 'time_start'
            await message.answer(TEXTS['add_game_time_start'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel_addgame')]]))
        elif step == 'time_start':
            state['time_start'] = message.text.strip()
            state['step'] = 'time_end'
            await message.answer(TEXTS['add_game_time_end'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel_addgame')]]))
        elif step == 'time_end':
            state['time_end'] = message.text.strip()
            state['step'] = 'place'
            await message.answer(TEXTS['add_game_place'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel_addgame')]]))
        elif step == 'place':
            state['place'] = message.text.strip()
            state['step'] = 'price'
            await message.answer(TEXTS['add_game_price'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel_addgame')]]))
        elif step == 'price':
            try:
                price = int(message.text.strip())
            except ValueError:
                await message.answer(TEXTS['add_game_price_error'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel_addgame')]]))
                return
            state['price'] = price
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute('INSERT INTO games (date, time_start, time_end, place, price) VALUES ($1, $2, $3, $4, $5)',
                                   state['date'], state['time_start'], state['time_end'], state['place'], state['price'])
            await message.answer(TEXTS['add_game_added'][lang], reply_markup=reply_menu(message.from_user.id in ADMIN_IDS, lang=lang))
            add_game_states.pop(message.from_user.id, None)
        return

    state = user_states.get(message.from_user.id, {})
    # --- Admin schedule edit mode ---
    if 'edit_game_id' in state:
        game_id = state['edit_game_id']
        # Expecting: date\ntime_start\ntime_end\nplace\nprice
        parts = message.text.strip().split('\n')
        if len(parts) != 5:
            await message.answer({'ru':'Ошибка! Введите расписание в формате:\nДата\nВремя начала\nВремя окончания\nМесто\nЦена',
                                 'uk':'Помилка! Введіть розклад у форматі:\nДата\nЧас початку\nЧас закінчення\nМісце\nЦіна',
                                 'en':'Error! Enter schedule in format:\nDate\nStart time\nEnd time\nPlace\nPrice'}[lang])
            return
        date, time_start, time_end, place, price = parts
        try:
            price_int = int(price)
        except ValueError:
            await message.answer({'ru':'Ошибка! Цена должна быть числом.',
                                 'uk':'Помилка! Ціна повинна бути числом.',
                                 'en':'Error! Price must be a number.'}[lang])
            return
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute('UPDATE games SET date = $1, time_start = $2, time_end = $3, place = $4, price = $5 WHERE id = $6',
                               date, time_start, time_end, place, price_int, game_id)
        user_states[message.from_user.id].pop('edit_game_id', None)
        await message.answer({'ru':'Расписание игры обновлено.','uk':'Розклад гри оновлено.','en':'Game schedule updated.'}[lang], reply_markup=reply_menu(message.from_user.id in ADMIN_IDS, lang=lang))
        return
    # --- Registration flow ---
    if 'registering' in state:
        step = state.get('step')
        if step == 'name':
            user_states[message.from_user.id]['full_name'] = message.text.strip()
            user_states[message.from_user.id]['step'] = 'username_choice'
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text={'ru':'Вставить мой автоматически','uk':'Вставити мій автоматично','en':'Insert mine automatically'}[lang], callback_data='auto_username')],
                [InlineKeyboardButton(text={'ru':'Ввести вручную','uk':'Ввести вручну','en':'Enter manually'}[lang], callback_data='manual_username')]
            ])
            await message.answer({'ru':'Выберите способ ввода username:','uk':'Виберіть спосіб введення username:','en':'Choose username input method:'}[lang], reply_markup=kb)
            return
        elif step == 'username':
            username = message.text.strip()
            if not username.startswith('@') or len(username) < 5:
                await message.answer({'ru':'Username должен начинаться с @ и быть не короче 5 символов. Скопируйте его из своего профиля Telegram.',
                                     'uk':'Username повинен починатися з @ і бути не коротше 5 символів. Скопіюйте його зі свого профілю Telegram.',
                                     'en':'Username must start with @ and be at least 5 characters. Copy it from your Telegram profile.'}[lang])
                await message.answer({'ru':'Пожалуйста, введите ваш username ещё раз:',
                                     'uk':'Будь ласка, введіть ваш username ще раз:',
                                     'en':'Please enter your username again:'}[lang])
                return
            # Проверка существования username через Telegram API
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://t.me/{username.lstrip('@')}"
                async with session.get(url) as resp:
                    page = await resp.text()
            if 'If you have Telegram, you can contact' in page or 'Send Message' in page:
                # username существует
                user_states[message.from_user.id]['username'] = username
                game_id = state['registering']
                full_name = state['full_name']
                pool = await get_pg_pool()
                async with pool.acquire() as conn:
                    await conn.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES ($1, $2, $3, $4, $5)',
                                       game_id, message.from_user.id, username, full_name, 0)
                await message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(message.from_user.id in ADMIN_IDS, lang=lang))
                user_states[message.from_user.id].pop('registering', None)
                user_states[message.from_user.id].pop('full_name', None)
                user_states[message.from_user.id].pop('username', None)
                user_states[message.from_user.id].pop('step', None)
                return
            else:
                await message.answer({'ru':'Такого username не существует в Telegram. Проверьте правильность и попробуйте ещё раз.',
                                     'uk':'Такого username не існує в Telegram. Перевірте правильність і спробуйте ще раз.',
                                     'en':'This username does not exist in Telegram. Check and try again.'}[lang])
                await message.answer({'ru':'Скопируйте ваш username из профиля Telegram. Откройте свой профиль, он начинается с @.',
                                     'uk':'Скопіюйте ваш username з профілю Telegram. Відкрийте свій профіль, він починається з @.',
                                     'en':'Copy your username from your Telegram profile. It starts with @.'}[lang])
                return
        elif step == 'username_choice':
            # Ожидается callback, не обрабатываем здесь
            return
    elif message.text and message.text.startswith('/togglepaid_'):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer(TEXTS['no_access'][lang])
            return
        reg_id = int(message.text.split('_')[1])
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow('SELECT paid FROM registrations WHERE id = $1', reg_id)
            if row is not None:
                new_paid = 0 if row['paid'] == 1 else 1
                await conn.execute('UPDATE registrations SET paid = $1 WHERE id = $2', new_paid, reg_id)
                await message.answer(f"{TEXTS['paid_status_changed'][lang]} {'✅' if new_paid else '❌'}.")
            else:
                await message.answer(TEXTS['record_not_found'][lang])
    else:
        await message.answer(TEXTS['unknown_command'][lang], reply_markup=reply_menu(message.from_user.id in ADMIN_IDS, lang=lang))
# Callback для username выбора
@dp.message(F.text.in_([
    '📝 Создать пост', '📝 Створити пост', '📝 Create post'
]))
async def create_post_start(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer('Нет доступа.')
        return
    user_states[message.from_user.id] = user_states.get(message.from_user.id, {})
    user_states[message.from_user.id]['create_post'] = True
    await message.answer('Введите текст поста:')

@dp.callback_query(F.data == 'add_schedule_btn')
async def post_with_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    post_text = user_states.get(user_id, {}).get('post_text', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📅 Расписание', callback_data='show_schedule')]
    ])
    # Получаем всех пользователей, которые когда-либо взаимодействовали с ботом
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch('SELECT user_id FROM users')
    # Если нет пользователей, отправляем только автору
    if not users:
        await callback.message.answer(post_text, reply_markup=kb)
    else:
        for user in users:
            uid = user['user_id']
            try:
                await bot.send_message(uid, post_text, reply_markup=kb)
            except Exception:
                pass
    user_states[user_id].pop('create_post', None)
    user_states[user_id].pop('post_text', None)
    await callback.message.delete()

@dp.callback_query(F.data == 'no_btn')
async def post_without_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    post_text = user_states.get(user_id, {}).get('post_text', '')
    await callback.message.answer(post_text)
    user_states[user_id].pop('create_post', None)
    user_states[user_id].pop('post_text', None)
    await callback.message.delete()

@dp.callback_query(F.data == 'show_schedule')
async def show_schedule_btn(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place, price FROM games')
    if not games:
        await callback.message.answer(TEXTS['schedule_empty'][lang])
        await callback.answer()
        return
    for game in games:
        game_id, date, time_start, time_end, place, price = game['id'], game['date'], game['time_start'], game['time_end'], game['place'], game['price']
        # Определяем день недели
        try:
            day, month, year = map(int, date.split('.'))
            dt = datetime.date(year, month, day)
            weekday = dt.strftime('%A')
            weekday_ru = {
                'Monday': 'Понедельник',
                'Tuesday': 'Вторник',
                'Wednesday': 'Среда',
                'Thursday': 'Четверг',
                'Friday': 'Пятница',
                'Saturday': 'Суббота',
                'Sunday': 'Воскресенье'
            }
            weekday_uk = {
                'Monday': 'Понеділок',
                'Tuesday': 'Вівторок',
                'Wednesday': 'Середа',
                'Thursday': 'Четвер',
                'Friday': 'Пʼятниця',
                'Saturday': 'Субота',
                'Sunday': 'Неділя'
            }
            weekday_en = {
                'Monday': 'Monday',
                'Tuesday': 'Tuesday',
                'Wednesday': 'Wednesday',
                'Thursday': 'Thursday',
                'Friday': 'Friday',
                'Saturday': 'Saturday',
                'Sunday': 'Sunday'
            }
            weekday_str = {'ru': weekday_ru, 'uk': weekday_uk, 'en': weekday_en}[lang][weekday]
        except Exception:
            weekday_str = ''
        # Fetch registrations from PostgreSQL
        registrations = await conn.fetch('SELECT full_name, username, paid FROM registrations WHERE game_id = $1 ORDER BY id', game_id)
        main_list = registrations[:14]
        reserve_list = registrations[14:]
        maps_url = f'https://www.google.com/maps/search/?api=1&query={place.replace(" ", "+")}'
        place_link = f'<a href="{maps_url}">{place}</a>'
        def name_link(name, username):
            if username:
                return f'<a href="https://t.me/{username.lstrip("@").strip()}">{name}</a>'
            return name
        reg_text = ""
        for idx, r in enumerate(main_list, 1):
            reg_text += f"{idx}. {name_link(r[0], r[1])} {'✅' if r[2] else ''}\n"
        if reserve_list:
            reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
            for idx, r in enumerate(reserve_list, 1):
                reg_text += f"R{idx}. {name_link(r[0], r[1])} {'✅' if r[2] else ''}\n"
        if not reg_text:
            reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
        text = (f"📅 {date} ({weekday_str})\n"
                f"⏰ {time_start} - {time_end}\n"
                f"🏟️ {place_link}\n"
                f"💵 {price} PLN\n"
                f"{ {'ru':'Записались:','uk':'Записались:','en':'Registered:'}[lang] }\n{reg_text}")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text={'ru':'Записаться','uk':'Записатися','en':'Register'}[lang], callback_data=f'register_{game_id}')],
        ])
        await callback.message.answer(text, reply_markup=kb, parse_mode='HTML', disable_web_page_preview=True)
    await callback.answer()

# --- Авто-вставка username ---
@dp.callback_query(F.data == 'auto_username')
async def auto_username(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_lang(user_id)
    tg_username = callback.from_user.username or ''
    # Используем имя/фамилию, введённые пользователем
    full_name = user_states[user_id].get('full_name')
    if not full_name:
        full_name = f"{callback.from_user.first_name or ''} {callback.from_user.last_name or ''}".strip()
    game_id = user_states[user_id].get('registering')
    if not game_id:
        await callback.message.answer({'ru':'Ошибка: не выбрана игра для регистрации.',
                                      'uk':'Помилка: не вибрано гру для реєстрації.',
                                      'en':'Error: no game selected for registration.'}[lang])
        return
    user_states[user_id]['username'] = tg_username
    user_states[user_id]['full_name'] = full_name
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES ($1, $2, $3, $4, $5)',
                           game_id, user_id, tg_username, full_name, 0)
    await callback.message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(user_id in ADMIN_IDS, lang=lang))
    user_states[user_id].pop('registering', None)
    user_states[user_id].pop('full_name', None)
    user_states[user_id].pop('username', None)
    user_states[user_id].pop('step', None)

@dp.callback_query(F.data == 'manual_username')
async def manual_username(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_lang(user_id)
    user_states[user_id]['step'] = 'username'
    await callback.message.answer({'ru':'Скопируйте ваш username из профиля Telegram. Откройте свой профиль, он начинается с @. Например: @nickname',
                                  'uk':'Скопіюйте ваш username з профілю Telegram. Відкрийте свій профіль, він починається з @. Наприклад: @nickname',
                                  'en':'Copy your username from your Telegram profile. It starts with @. Example: @nickname'}[lang], reply_markup=None)

@dp.callback_query(F.data == 'delete_player_mode')
async def delete_player_mode(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer(TEXTS['no_access'][lang])
        return
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place FROM games')
        if not games:
            await callback.message.answer({'ru':'Нет доступных игр.','uk':'Немає доступних ігор.','en':'No available games.'}[lang])
            return
        for game in games:
            game_id, date, time_start, time_end, place = game['id'], game['date'], game['time_start'], game['time_end'], game['place']
            registrations = await conn.fetch('SELECT id, full_name, paid FROM registrations WHERE game_id = $1 ORDER BY id', game_id)
            main_list = registrations[:14]
            reserve_list = registrations[14:]
            reg_text = ""
            kb_rows = []
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {r['full_name']} {'✅' if r['paid'] else ''}\n"
            kb_rows.append([InlineKeyboardButton(text={'ru':f"Удалить: {r['full_name']}", 'uk':f"Видалити: {r['full_name']}", 'en':f"Delete: {r['full_name']}"}[lang], callback_data=f"deladminreg_{r['id']}")])
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {r['full_name']} {'✅' if r['paid'] else ''}\n"
                    kb_rows.append([InlineKeyboardButton(text={'ru':f"Удалить: {r['full_name']}", 'uk':f"Видалити: {r['full_name']}", 'en':f"Delete: {r['full_name']}"}[lang], callback_data=f"deladminreg_{r['id']}")])
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
            text = (f"📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place} \n{reg_text}")
            kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
            await callback.message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith('deladminreg_'))
async def deladminreg(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    reg_id = int(callback.data.split('_')[1])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM registrations WHERE id = $1', reg_id)
    await callback.message.answer({'ru':'Запись удалена.','uk':'Запис видалено.','en':'Registration deleted.'}[lang])

# Helper: delete previous bot message for user
async def delete_last_bot_message(user_id, chat):
    msg_id = user_states.get(user_id, {}).get('last_bot_msg_id')
    if msg_id:
        try:
            await bot.delete_message(chat.id, msg_id)
        except Exception:
            pass
        user_states[user_id]['last_bot_msg_id'] = None

# --- Запуск бота ---
if __name__ == "__main__":
    import logging
    import threading
    from aiohttp import web

    logging.basicConfig(level=logging.INFO)

    async def on_startup(dispatcher):
        await init_db()

    # Minimal HTTP server for Render health check
    async def handle(request):
        return web.Response(text="OK")

    def run_web():
        app = web.Application()
        app.router.add_get("/", handle)
        port = int(os.environ.get("PORT", 10000))
        web.run_app(app, port=port)

    # Start HTTP server in a separate thread
    threading.Thread(target=run_web, daemon=True).start()

    dp.startup.register(on_startup)
    dp.run_polling(bot)