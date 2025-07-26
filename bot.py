async def init_db():
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Ensure posts table exists
        await conn.execute('''CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            text TEXT,
            created_at TIMESTAMP
        )''')
        # Ensure extra_info column exists in games table
        await conn.execute('''CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            date TEXT,
            time_start TEXT,
            time_end TEXT,
            place TEXT,
            price INTEGER
        )''')
        # Add extra_info column if missing (safe check)
        col_check = await conn.fetchval("SELECT column_name FROM information_schema.columns WHERE table_name='games' AND column_name='extra_info'")
        if not col_check:
            try:
                await conn.execute('ALTER TABLE games ADD COLUMN extra_info TEXT')
            except Exception:
                pass  # Ignore if column already exists
        
        # Create registrations table with BIGINT for user_id
        await conn.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id SERIAL PRIMARY KEY,
            game_id INTEGER,
            user_id BIGINT,
            username TEXT,
            full_name TEXT,
            paid INTEGER DEFAULT 0
        )''')
        
        # Create users table with BIGINT for user_id
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            lang TEXT
        )''')
        
        # Check if we need to alter existing tables to use BIGINT
        try:
            # Check registrations table
            reg_user_id_type = await conn.fetchval("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name='registrations' AND column_name='user_id'
            """)
            if reg_user_id_type == 'integer':
                await conn.execute('ALTER TABLE registrations ALTER COLUMN user_id TYPE BIGINT')
                
            # Check users table  
            users_user_id_type = await conn.fetchval("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name='users' AND column_name='user_id'
            """)
            if users_user_id_type == 'integer':
                await conn.execute('ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT')
        except Exception as e:
            print(f"Note: Could not alter existing tables: {e}")
            # This is okay - tables might not exist yet or already be correct type
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
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
import asyncpg
import datetime

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or '7552454167:AAGJCiF2yiQ-oMokKORBHosgdAHzgLei74U'

ADMIN_IDS = [760746564, 683243528, 1202044081]
# Railway использует DATABASE_URL, Render использует POSTGRES_DSN
DB_DSN = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN') or 'postgresql://postgres:postgres@localhost:5432/volleyball'

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_states = {}
add_game_states = {}

@dp.callback_query(F.data == 'main_schedule')
async def main_schedule_btn(callback: CallbackQuery):
    await show_schedule(callback.message)
    await callback.answer()
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
    # --- Add game step handler is defined below ---

# --- Delete game menu ---
@dp.message(F.text.in_(['❌ Удалить игру','❌ Видалити гру','❌ Delete game']))
async def delete_game_menu(message: Message):
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
    lang = get_lang(message.from_user.id)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(TEXTS['no_access'][lang])
        return
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place FROM games')
        if not games:
            await message.answer(TEXTS['delete_game_empty'][lang])
            return
        kb_rows = []
        for game in games:
            game_id, date, time_start, time_end, place = game['id'], game['date'], game['time_start'], game['time_end'], game['place']
            kb_rows.append([InlineKeyboardButton(text=f"{date} {time_start}-{time_end} {place}", callback_data=f'delgame_{game_id}')])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await message.answer(TEXTS['delete_game_choose'][lang], reply_markup=kb)

# --- Create post menu ---
@dp.message(F.text.in_(['📝 Создать пост','📝 Створити пост','📝 Create post']))
async def create_post_menu(message: Message):
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    
    lang = get_lang(message.from_user.id)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(TEXTS['no_access'][lang])
        return
    user_id = message.from_user.id
    # Preserve language in state if already set
    lang_state = user_states.get(user_id, {}).get('lang', lang)
    user_states[user_id] = {'step': 'create_post', 'lang': lang_state}
    await message.answer({'ru':'Введите текст поста:','uk':'Введіть текст поста:','en':'Enter post text:'}[lang])

# --- Create post step handler ---
# ...existing code...

TEXTS = {
    'welcome': {
        'ru': "Добро пожаловать! Выберите язык:",
        'uk': "Ласкаво просимо! Виберіть мову:",
        'en': "Welcome! Choose your language:"
    },
    'welcome_description': {
        'ru': "🏐 Играем волейбол в Варшаве — зал, мячи, организация за 25–29 PLN.\n📅 Расписание обновляется каждый понедельник в 12:00.\n📝 Записывайся на игры прямо тут!",
        'uk': "🏐 Граємо у волейбол у Варшаві — зал, м'ячі, організація за 25–29 PLN.\n📅 Розклад оновлюється щопонеділка о 12:00.\n📝 Записуйся на ігри прямо тут!",
        'en': "🏐 Playing volleyball in Warsaw — hall, balls, organization for 25–29 PLN.\n📅 Schedule is updated every Monday at 12:00.\n📝 Sign up for games right here!"
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

async def ensure_user_lang(user_id):
    """Убеждается, что язык пользователя загружен в user_states"""
    if user_id not in user_states or 'lang' not in user_states[user_id]:
        # Загружаем из базы данных
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            user_data = await conn.fetchrow('SELECT lang FROM users WHERE user_id = $1', user_id)
            if user_data:
                lang = user_data['lang'] if user_data['lang'] else 'ru'
            else:
                # Новый пользователь - создаем запись в базе
                lang = 'ru'
                await conn.execute('INSERT INTO users (user_id, lang) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING', user_id, lang)
            
            # Обновляем user_states
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]['lang'] = lang
    
    return user_states[user_id]['lang']

@dp.message(F.text.in_([
    '⚙️ Параметры', '⚙️ Параметри', '⚙️ Parameters'
]))
async def parameters_menu(message: Message):
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
    user_id = message.from_user.id
    
    # Убеждаемся, что язык пользователя загружен
    lang = await ensure_user_lang(user_id)
    
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

@dp.callback_query(F.data.startswith('lang_') & F.data.endswith('_first'))
async def set_language_first_time(callback: CallbackQuery):
    # Обработчик для выбора языка при первом запуске
    lang = callback.data.split('_')[1]  # Извлекаем язык из callback_data типа 'lang_ru_first'
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    # Сохраняем язык в состоянии пользователя
    user_states[user_id] = {'lang': lang}
    
    # Сохраняем пользователя в базу данных
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id, lang) VALUES ($1, $2)', user_id, lang)
    
    # Показываем приветственное описание бота
    welcome_description = TEXTS['welcome_description'][lang]
    await callback.message.edit_text(welcome_description, reply_markup=reply_menu(is_admin, lang))
    await callback.answer()

def clear_add_game_state(user_id):
    """Очищает состояние добавления игры для пользователя"""
    add_game_states.pop(user_id, None)

def clear_post_creation_state(user_id):
    """Очищает состояние создания поста для пользователя"""
    if user_id in user_states:
        user_states[user_id].pop('step', None)
        user_states[user_id].pop('post_text', None)

@dp.message(F.text.in_([
    '📅 Расписание', '📅 Розклад', '📅 Schedule'
]))
async def show_schedule(message: Message):
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
    user_id = message.from_user.id
    
    # Убеждаемся, что язык пользователя загружен
    lang = await ensure_user_lang(user_id)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        games = await conn.fetch('SELECT id, date, time_start, time_end, place, price, extra_info FROM games')
        if not games:
            await message.answer(TEXTS['schedule_empty'][lang])
            return

        for game in games:
            game_id, date, time_start, time_end, place, price, extra_info = game['id'], game['date'], game['time_start'], game['time_end'], game['place'], game['price'], game.get('extra_info', '')
            # Определяем день недели и скрываем год
            try:
                day, month, year = map(int, date.split('.'))
                dt = datetime.date(year, month, day)
                weekday = dt.strftime('%A')
                weekday_short_ru = {
                    'Monday': 'пн', 'Tuesday': 'вт', 'Wednesday': 'ср', 'Thursday': 'чт', 'Friday': 'пт', 'Saturday': 'сб', 'Sunday': 'вс'
                }
                weekday_short_uk = {
                    'Monday': 'пн', 'Tuesday': 'вт', 'Wednesday': 'ср', 'Thursday': 'чт', 'Friday': 'пт', 'Saturday': 'сб', 'Sunday': 'нд'
                }
                weekday_short_en = {
                    'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed', 'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun'
                }
                weekday_short_map = {'ru': weekday_short_ru, 'uk': weekday_short_uk, 'en': weekday_short_en}
                weekday_str = weekday_short_map.get(lang, weekday_short_en).get(weekday)
                if not weekday_str:
                    weekday_str = weekday_short_en.get(weekday, weekday)
                # Форматируем дату без года
                date_no_year = '.'.join(date.split('.')[:2])
            except Exception:
                weekday_str = ''
                date_no_year = date
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
            extra_info_text = f"📝 {extra_info}\n" if extra_info else ""
            text = (f"📅 {date_no_year} ({weekday_str})\n"
                    f"⏰ {time_start} - {time_end}\n"
                    f"🏟️ {place_link}\n"
                    f"💵 {price} PLN\n"
                    f"{extra_info_text}"
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
    # Очищаем состояние добавления игры при начале регистрации
    clear_add_game_state(callback.from_user.id)
    # Очищаем состояние создания поста при начале регистрации
    clear_post_creation_state(callback.from_user.id)
    
    user_id = callback.from_user.id
    
    # Убеждаемся, что язык пользователя загружен
    lang = await ensure_user_lang(user_id)
    
    game_id = int(callback.data.split('_')[1])
    user_states[user_id]['registering'] = game_id

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
    user_id = callback.from_user.id
    lang = await ensure_user_lang(user_id)
    previous = user_states[user_id].get('previous', [])
    seen = set()
    unique_previous = []
    for name, username in previous:
        key = (name.strip(), (username or '').strip())
        if key not in seen:
            seen.add(key)
            unique_previous.append((name, username))
    # Helper: delete previous bot message for user
    async def delete_last_bot_message(user_id, chat):
        msg_id = user_states.get(user_id, {}).get('last_bot_msg_id')
        if msg_id:
            try:
                await bot.delete_message(chat.id, msg_id)
            except Exception:
                pass
            user_states[user_id]['last_bot_msg_id'] = None
    await delete_last_bot_message(callback.from_user.id, callback.message.chat)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{name}', callback_data=f'prev_{name}_{username}') for name, username in unique_previous]
    ])
    msg = await callback.message.answer({'ru':'Выберите игрока:','uk':'Виберіть гравця:','en':'Choose player:'}[lang], reply_markup=kb)
    user_states[callback.from_user.id]['last_bot_msg_id'] = msg.message_id

@dp.callback_query(F.data.startswith('prev_'))
async def prev_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await ensure_user_lang(user_id)
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
    user_id = callback.from_user.id
    lang = await ensure_user_lang(user_id)
    user_states[callback.from_user.id]['step'] = 'name'
    await callback.message.answer(TEXTS['enter_name'][lang])

@dp.message(F.text.in_([
    '➕ Добавить игру', '➕ Додати гру', '➕ Add game'
]))
async def add_game_menu(message: Message):
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
    lang = get_lang(message.from_user.id)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(TEXTS['no_access'][lang])
        return
    add_game_states[message.from_user.id] = {'step': 'date'}
    await message.answer(TEXTS['add_game_date'][lang], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text={'ru':'Отмена','uk':'Скасувати','en':'Cancel'}[lang], callback_data='cancel_addgame')]]))

# --- Add game step handler ---
    # ...existing code...

# --- Skip extra info callback ---
@dp.callback_query(F.data == 'skip_extra_info')
async def skip_extra_info(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_lang(user_id)
    state = add_game_states.get(user_id)
    if not state or state.get('step') != 'extra_info':
        await callback.answer()
        return
    state['extra_info'] = ''
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO games (date, time_start, time_end, place, price, extra_info) VALUES ($1, $2, $3, $4, $5, $6)',
                           state['date'], state['time_start'], state['time_end'], state['place'], state['price'], state['extra_info'])
    add_game_states.pop(user_id, None)
    await callback.message.answer(TEXTS['add_game_added'][lang], reply_markup=reply_menu(True, lang))
    await callback.answer()

@dp.callback_query(F.data == 'post_with_schedule_button')
async def post_with_schedule_button(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    user_id = callback.from_user.id
    state = user_states.get(user_id)
    
    if not state or state.get('step') != 'post_button_choice':
        await callback.answer()
        return
        
    post_text = state.get('post_text')
    if not post_text:
        await callback.message.answer({'ru':'Ошибка: текст поста не найден.','uk':'Помилка: текст посту не знайдено.','en':'Error: post text not found.'}[lang])
        await callback.answer()
        return
    
    # Создаем кнопку расписания
    schedule_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text={'ru':'📅 Расписание','uk':'📅 Розклад','en':'📅 Schedule'}[lang], callback_data='main_schedule')]
    ])
    
    # Сохраняем пост в базу данных
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO posts (text, created_at) VALUES ($1, $2)', post_text, datetime.datetime.now())
        users = await conn.fetch('SELECT user_id FROM users')
    
    # Отправляем пост всем пользователям с кнопкой
    sent_count = 0
    for u in users:
        try:
            await bot.send_message(u['user_id'], post_text, reply_markup=schedule_button)
            sent_count += 1
        except Exception:
            pass
    
    user_states.pop(user_id, None)
    await callback.message.answer({'ru':f'Пост с кнопкой отправлен {sent_count} пользователям!','uk':f'Пост з кнопкою надіслано {sent_count} користувачам!','en':f'Post with button sent to {sent_count} users!'}[lang], reply_markup=reply_menu(True, lang))
    await callback.answer()

@dp.callback_query(F.data == 'post_without_button')
async def post_without_button(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    user_id = callback.from_user.id
    state = user_states.get(user_id)
    
    if not state or state.get('step') != 'post_button_choice':
        await callback.answer()
        return
        
    post_text = state.get('post_text')
    if not post_text:
        await callback.message.answer({'ru':'Ошибка: текст поста не найден.','uk':'Помилка: текст посту не знайдено.','en':'Error: post text not found.'}[lang])
        await callback.answer()
        return
    
    # Сохраняем пост в базу данных
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO posts (text, created_at) VALUES ($1, $2)', post_text, datetime.datetime.now())
        users = await conn.fetch('SELECT user_id FROM users')
    
    # Отправляем пост всем пользователям без кнопки
    sent_count = 0
    for u in users:
        try:
            await bot.send_message(u['user_id'], post_text)
            sent_count += 1
        except Exception:
            pass
    
    user_states.pop(user_id, None)
    await callback.message.answer({'ru':f'Пост отправлен {sent_count} пользователям!','uk':f'Пост надіслано {sent_count} користувачам!','en':f'Post sent to {sent_count} users!'}[lang], reply_markup=reply_menu(True, lang))
    await callback.answer()

@dp.callback_query(F.data == 'cancel_addgame')
async def cancel_addgame(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    add_game_states.pop(callback.from_user.id, None)
    await callback.message.answer({'ru':'Создание игры отменено.','uk':'Створення гри скасовано.','en':'Game creation cancelled.'}[lang], reply_markup=reply_menu(callback.from_user.id in ADMIN_IDS, lang=lang))

@dp.message(F.text.in_([
    '🎟 Мои записи', '🎟 Мої записи', '🎟 My records'
]))
async def my_records(message: Message):
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
    user_id = message.from_user.id
    
    # Убеждаемся, что язык пользователя загружен
    lang = await ensure_user_lang(user_id)
    
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
    # Очищаем состояние добавления игры при переходе к другому действию
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при переходе к другому действию
    clear_post_creation_state(message.from_user.id)
    
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
        # Формируем блок для копирования и редактирования
        schedule_block = f"{date}\n{time_start}\n{time_end}\n{place}\n{price}"
        # Добавляем extra_info если есть
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            extra_info = await conn.fetchval('SELECT extra_info FROM games WHERE id = $1', game_id)
        if extra_info:
            schedule_block += f"\n{extra_info}"
        # Инструкция для админа
        instructions = {
            'ru': "Скопируйте, отредактируйте и отправьте новое расписание в этом формате:\nДата\nВремя начала\nВремя окончания\nМесто\nЦена\nЗаметки (опционально)",
            'uk': "Скопіюйте, відредагуйте і надішліть новий розклад у цьому форматі:\nДата\nЧас початку\nЧас закінчення\nМісце\nЦіна\nНотатки (опціонально)",
            'en': "Copy, edit, and send the new schedule in this format:\nDate\nStart time\nEnd time\nPlace\nPrice\nExtra info (optional)"
        }[lang]
        user_states[callback.from_user.id]['edit_game_mode'] = True
        await callback.message.answer(f"{instructions}\n\n<pre>{schedule_block}</pre>", parse_mode='HTML')
    else:
        await callback.message.answer({'ru':'Игра не найдена.','uk':'Гру не знайдено.','en':'Game not found.'}[lang])

@dp.message(CommandStart())
async def start_command(message: Message):
    # Очищаем состояние добавления игры при команде /start
    clear_add_game_state(message.from_user.id)
    # Очищаем состояние создания поста при команде /start
    clear_post_creation_state(message.from_user.id)
    
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    # Проверяем, есть ли пользователь в базе данных
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        existing_user = await conn.fetchrow('SELECT user_id, lang FROM users WHERE user_id = $1', user_id)
    
    if existing_user:
        # Пользователь уже существует, показываем описание и меню
        lang = existing_user['lang'] if existing_user['lang'] else 'ru'
        user_states[user_id] = {'lang': lang}
        
        welcome_description = TEXTS['welcome_description'][lang]
        await message.answer(welcome_description, reply_markup=reply_menu(is_admin, lang))
    else:
        # Новый пользователь, предлагаем выбрать язык
        welcome_text = TEXTS['welcome']['uk']  # Показываем приветствие на украинском по умолчанию
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES['ru'], callback_data='lang_ru_first')],
            [InlineKeyboardButton(text=LANGUAGES['uk'], callback_data='lang_uk_first')],
            [InlineKeyboardButton(text=LANGUAGES['en'], callback_data='lang_en_first')]
        ])
        await message.answer(welcome_text, reply_markup=kb)

@dp.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    
    # Убеждаемся, что язык пользователя загружен
    lang = await ensure_user_lang(user_id)

    # --- Create post step handler ---
    state = user_states.get(user_id)
    if state and state.get('step') == 'create_post':
        post_text = message.text.strip()
        if not post_text:
            await message.answer({'ru':'Текст поста не может быть пустым.','uk':'Текст посту не може бути порожнім.','en':'Post text cannot be empty.'}[lang])
            return
        # Сохраняем текст поста в состоянии пользователя
        user_states[user_id]['post_text'] = post_text
        user_states[user_id]['step'] = 'post_button_choice'
        
        # Предлагаем выбор с кнопками
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text={'ru':'📅 С кнопкой "Расписание"','uk':'📅 З кнопкою "Розклад"','en':'📅 With "Schedule" button'}[lang], callback_data='post_with_schedule_button')],
            [InlineKeyboardButton(text={'ru':'📝 Без кнопки','uk':'📝 Без кнопки','en':'📝 Without button'}[lang], callback_data='post_without_button')]
        ])
        await message.answer({'ru':'Добавить кнопку расписания под постом?','uk':'Додати кнопку розкладу під постом?','en':'Add schedule button under the post?'}[lang], reply_markup=kb)
        return

    # --- Edit game step handler ---
    if state and state.get('edit_game_mode') and user_id in ADMIN_IDS:
        game_id = state.get('edit_game_id')
        if not game_id:
            await message.answer({'ru':'Ошибка: игра для редактирования не найдена.','uk':'Помилка: гру для редагування не знайдено.','en':'Error: game for editing not found.'}[lang])
            return
        
        lines = message.text.strip().split('\n')
        if len(lines) < 5:
            await message.answer({'ru':'Ошибка: неправильный формат. Нужно:\nДата\nВремя начала\nВремя окончания\nМесто\nЦена\nЗаметки (опционально)','uk':'Помилка: неправильний формат. Потрібно:\nДата\nЧас початку\nЧас закінчення\nМісце\nЦіна\nНотатки (опціонально)','en':'Error: wrong format. Need:\nDate\nStart time\nEnd time\nPlace\nPrice\nExtra info (optional)'}[lang])
            return
        
        try:
            date = lines[0].strip()
            time_start = lines[1].strip()
            time_end = lines[2].strip()
            place = lines[3].strip()
            price = int(lines[4].strip())
            extra_info = lines[5].strip() if len(lines) > 5 else ''
            
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    'UPDATE games SET date = $1, time_start = $2, time_end = $3, place = $4, price = $5, extra_info = $6 WHERE id = $7',
                    date, time_start, time_end, place, price, extra_info, game_id
                )
            
            # Очищаем состояние
            user_states[user_id].pop('edit_game_mode', None)
            user_states[user_id].pop('edit_game_id', None)
            
            await message.answer({'ru':'Расписание обновлено!','uk':'Розклад оновлено!','en':'Schedule updated!'}[lang], reply_markup=reply_menu(True, lang))
            return
            
        except ValueError:
            await message.answer({'ru':'Ошибка: цена должна быть числом.','uk':'Помилка: ціна має бути числом.','en':'Error: price must be a number.'}[lang])
            return
        except Exception as e:
            await message.answer({'ru':'Ошибка при обновлении расписания.','uk':'Помилка при оновленні розкладу.','en':'Error updating schedule.'}[lang])
            return

    # --- Toggle paid status for registration ---
    if message.text and message.text.startswith('/togglepaid_') and user_id in ADMIN_IDS:
        try:
            reg_id = int(message.text.split('_')[1])
        except Exception:
            await message.answer({'ru':'Ошибка: неверный формат команды.','uk':'Помилка: невірний формат команди.','en':'Error: invalid command format.'}[lang])
            return
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            reg = await conn.fetchrow('SELECT paid FROM registrations WHERE id = $1', reg_id)
            if not reg:
                await message.answer({'ru':'Запись не найдена.','uk':'Запис не знайдено.','en':'Registration not found.'}[lang])
                return
            new_paid = 0 if reg['paid'] else 1
            await conn.execute('UPDATE registrations SET paid = $1 WHERE id = $2', new_paid, reg_id)
        await message.answer(f"{TEXTS['paid_status_changed'][lang]} {'✅' if new_paid else '❌'}", reply_markup=reply_menu(True, lang))
        return

    # --- Add game step handler ---
    add_state = add_game_states.get(user_id)
    if add_state:
        step = add_state.get('step')
        text = message.text.strip()
        if step == 'date':
            add_state['date'] = text
            add_state['step'] = 'time_start'
            await message.answer(TEXTS['add_game_time_start'][lang])
            return
        elif step == 'time_start':
            add_state['time_start'] = text
            add_state['step'] = 'time_end'
            await message.answer(TEXTS['add_game_time_end'][lang])
            return
        elif step == 'time_end':
            add_state['time_end'] = text
            add_state['step'] = 'place'
            await message.answer(TEXTS['add_game_place'][lang])
            return
        elif step == 'place':
            add_state['place'] = text
            add_state['step'] = 'price'
            await message.answer(TEXTS['add_game_price'][lang])
            return
        elif step == 'price':
            try:
                price = int(text)
            except Exception:
                await message.answer(TEXTS['add_game_price_error'][lang])
                return
            add_state['price'] = price
            add_state['step'] = 'extra_info'
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text={'ru':'Пропустить','uk':'Пропустити','en':'Skip'}[lang], callback_data='skip_extra_info')]])
            await message.answer({'ru':'Введите заметки (опционально):','uk':'Введіть нотатки (опціонально):','en':'Enter extra info (optional):'}[lang], reply_markup=kb)
            return
        elif step == 'extra_info':
            add_state['extra_info'] = text
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute('INSERT INTO games (date, time_start, time_end, place, price, extra_info) VALUES ($1, $2, $3, $4, $5, $6)',
                                   add_state['date'], add_state['time_start'], add_state['time_end'], add_state['place'], add_state['price'], add_state['extra_info'])
            add_game_states.pop(user_id, None)
            await message.answer(TEXTS['add_game_added'][lang], reply_markup=reply_menu(True, lang))
            return

    # --- Registration flow: handle step 'name' ---
    if user_id in user_states and user_states[user_id].get('step') == 'name':
        full_name = message.text.strip()
        user_states[user_id]['full_name'] = full_name
        user_states[user_id]['step'] = 'username'
        # Show two buttons: auto-insert and manual entry
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text={'ru':'Авто-вставка','uk':'Автовставка','en':'Auto-insert'}[lang], callback_data='auto_username')],
            [InlineKeyboardButton(text={'ru':'Ввести вручную','uk':'Ввести вручну','en':'Enter manually'}[lang], callback_data='manual_username')]
        ])
        await message.answer(TEXTS['enter_username'][lang], reply_markup=kb)
        return

    # --- Registration flow: handle step 'username' (manual entry) ---
    if user_id in user_states and user_states[user_id].get('step') == 'username':
        username = message.text.strip()
        user_states[user_id]['username'] = username
        game_id = user_states[user_id].get('registering')
        full_name = user_states[user_id].get('full_name')
        if not game_id or not full_name:
            await message.answer({'ru':'Ошибка: не выбрана игра для регистрации.',
                                  'uk':'Помилка: не вибрано гру для реєстрації.',
                                  'en':'Error: no game selected for registration.'}[lang])
            return
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES ($1, $2, $3, $4, $5)',
                               game_id, user_id, username, full_name, 0)
        await message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(user_id in ADMIN_IDS, lang=lang))
        user_states[user_id].pop('registering', None)
        user_states[user_id].pop('full_name', None)
        user_states[user_id].pop('username', None)
        user_states[user_id].pop('step', None)
        return
@dp.callback_query(F.data == 'auto_username')
async def auto_username(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await ensure_user_lang(user_id)
    tg_username = callback.from_user.username or ''
    user_states[user_id]['username'] = tg_username
    game_id = user_states[user_id].get('registering')
    full_name = user_states[user_id].get('full_name')
    if not game_id or not full_name:
        await callback.message.answer({'ru':'Ошибка: не выбрана игра для регистрации.',
                                      'uk':'Помилка: не вибрано гру для реєстрації.',
                                      'en':'Error: no game selected for registration.'}[lang])
        return
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES ($1, $2, $3, $4, $5)',
                           game_id, user_id, tg_username, full_name, 0)
    await callback.message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(user_id in ADMIN_IDS, lang=lang))
    user_states[user_id].pop('registering', None)
    user_states[user_id].pop('full_name', None)
    user_states[user_id].pop('username', None)
    user_states[user_id].pop('step', None)
    await callback.answer()


@dp.callback_query(F.data == 'manual_username')
async def manual_username(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await ensure_user_lang(user_id)
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
            
            # Создаем кнопки для основного списка
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {r['full_name']} {'✅' if r['paid'] else ''}\n"
                kb_rows.append([InlineKeyboardButton(text={'ru':f"Удалить: {r['full_name']}", 'uk':f"Видалити: {r['full_name']}", 'en':f"Delete: {r['full_name']}"}[lang], callback_data=f"deladminreg_{r['id']}")])
            
            # Создаем кнопки для резервного списка
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {r['full_name']} {'✅' if r['paid'] else ''}\n"
                    kb_rows.append([InlineKeyboardButton(text={'ru':f"Удалить: {r['full_name']}", 'uk':f"Видалити: {r['full_name']}", 'en':f"Delete: {r['full_name']}"}[lang], callback_data=f"deladminreg_{r['id']}")])
            
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
            
            text = (f"📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place} \n{reg_text}")
            
            # Создаем клавиатуру только если есть кнопки
            if kb_rows:
                kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
                await callback.message.answer(text, reply_markup=kb)
            else:
                await callback.message.answer(text)


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


    # For local development, comment out the HTTP server block below:
    # For production deployment (Render, Heroku, etc.), uncomment the HTTP server block:
    
    # Проверяем, запущен ли бот в продакшене (есть переменная PORT)
    if os.getenv("PORT"):
        # Режим продакшена - запускаем веб-сервер для Render/Heroku
        async def handle(request):
            return web.Response(text="Bot is running!")

        def run_web():
            try:
                app = web.Application()
                app.router.add_get("/", handle)
                port = int(os.environ.get("PORT", 10000))
                web.run_app(app, port=port, host="0.0.0.0")
            except Exception as e:
                print(f"Web server error: {e}")

        threading.Thread(target=run_web, daemon=True).start()
        print(f"Web server started on port {os.getenv('PORT', 10000)}")

    dp.startup.register(on_startup)
    dp.run_polling(bot)