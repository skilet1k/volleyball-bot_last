import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
import aiosqlite

import os
import os
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = 760746564
DB_PATH = 'volleyball.db'

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_states = {}
add_game_states = {}

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
        [KeyboardButton(text={'ru':'⚙️ Настройки','uk':'⚙️ Налаштування','en':'⚙️ Settings'}[lang])]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text={'ru':'➕ Добавить игру','uk':'➕ Додати гру','en':'➕ Add game'}[lang])])
        buttons.append([KeyboardButton(text={'ru':'❌ Удалить игру','uk':'❌ Видалити гру','en':'❌ Delete game'}[lang])])
        buttons.append([KeyboardButton(text={'ru':'👥 Просмотреть записи','uk':'👥 Переглянути записи','en':'👥 View registrations'}[lang])])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time_start TEXT,
            time_end TEXT,
            place TEXT,
            price INTEGER
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            paid INTEGER DEFAULT 0
        )''')
        await db.commit()

@dp.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES['ru'], callback_data='lang_ru')],
        [InlineKeyboardButton(text=LANGUAGES['uk'], callback_data='lang_uk')],
        [InlineKeyboardButton(text=LANGUAGES['en'], callback_data='lang_en')]
    ])
    user_states[message.from_user.id] = {}
    await message.answer(TEXTS['welcome']['uk'], reply_markup=kb)

@dp.message(F.text.in_([
    '⚙️ Настройки', '⚙️ Налаштування', '⚙️ Settings'
]))
async def settings_menu(message: Message):
    lang = get_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES['ru'], callback_data='lang_ru')],
        [InlineKeyboardButton(text=LANGUAGES['uk'], callback_data='lang_uk')],
        [InlineKeyboardButton(text=LANGUAGES['en'], callback_data='lang_en')]
    ])
    await message.answer({'ru':'Выберите язык:','uk':'Виберіть мову:','en':'Choose language:'}[lang], reply_markup=kb)

@dp.callback_query(F.data.startswith('lang_'))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split('_')[1]
    user_states[callback.from_user.id] = {'lang': lang}
    is_admin = callback.from_user.id == ADMIN_ID
    await callback.message.answer({'ru':'Язык изменён.','uk':'Мову змінено.','en':'Language changed.'}[lang], reply_markup=reply_menu(is_admin, lang))
    await callback.answer()

@dp.message(F.text.in_([
    '📅 Расписание', '📅 Розклад', '📅 Schedule'
]))
async def show_schedule(message: Message):
    lang = get_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id, date, time_start, time_end, place, price FROM games')
        games = await cursor.fetchall()

        if not games:
            await message.answer(TEXTS['schedule_empty'][lang])
            return

        for game in games:
            game_id, date, time_start, time_end, place, price = game

            reg_cursor = await db.execute('SELECT full_name, paid FROM registrations WHERE game_id = ? ORDER BY id', (game_id,))
            registrations = await reg_cursor.fetchall()

            main_list = registrations[:14]
            reserve_list = registrations[14:]

            reg_text = ""
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {r[0]} {'✅' if r[1] else '❌'}\n"
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {r[0]} {'✅' if r[1] else '❌'}\n"
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]

            text = (f"📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place} 💵 {price} PLN\n"
                    f"{ {'ru':'Записались:','uk':'Записались:','en':'Registered:'}[lang] }\n{reg_text}")

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text={'ru':'Записаться','uk':'Записатися','en':'Register'}[lang], callback_data=f'register_{game_id}')]
            ])
            await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith('register_'))
async def register(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    game_id = int(callback.data.split('_')[1])
    if callback.from_user.id not in user_states:
        user_states[callback.from_user.id] = {'lang': lang}
    user_states[callback.from_user.id]['registering'] = game_id
    await callback.message.answer(TEXTS['enter_name'][lang])

@dp.message(F.text.in_([
    '👥 Просмотреть записи', '👥 Переглянути записи', '👥 View registrations'
]))
async def view_records(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id != ADMIN_ID:
        await message.answer(TEXTS['no_access'][lang])
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id, date, time_start, time_end, place FROM games')
        games = await cursor.fetchall()
        if not games:
            await message.answer({'ru':'Нет доступных игр.','uk':'Немає доступних ігор.','en':'No available games.'}[lang])
            return
        for game in games:
            game_id, date, time_start, time_end, place = game
            reg_cursor = await db.execute('SELECT id, full_name, paid FROM registrations WHERE game_id = ? ORDER BY id', (game_id,))
            registrations = await reg_cursor.fetchall()
            main_list = registrations[:14]
            reserve_list = registrations[14:]
            reg_text = ""
            for idx, r in enumerate(main_list, 1):
                reg_text += f"{idx}. {r[1]} {'✅' if r[2] else '❌'} | /togglepaid_{r[0]}\n"
            if reserve_list:
                reg_text += "\n" + {'ru':'Резерв:','uk':'Резерв:','en':'Reserve:'}[lang] + "\n"
                for idx, r in enumerate(reserve_list, 1):
                    reg_text += f"R{idx}. {r[1]} {'✅' if r[2] else '❌'} | /togglepaid_{r[0]}\n"
            if not reg_text:
                reg_text = {'ru':'Нет записанных.','uk':'Немає записаних.','en':'No registrations.'}[lang]
            await message.answer(f"{ {'ru':'Игра','uk':'Гра','en':'Game'}[lang] } 📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place}\n{reg_text}")

@dp.message(F.text.in_([
    '🎟 Мои записи', '🎟 Мої записи', '🎟 My records'
]))
async def my_records(message: Message):
    lang = get_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''SELECT r.id, g.date, g.time_start, g.time_end, g.place, r.full_name, r.paid
                                     FROM registrations r
                                     JOIN games g ON r.game_id = g.id
                                     WHERE r.user_id = ?''', (message.from_user.id,))
        records = await cursor.fetchall()

    if not records:
        await message.answer(TEXTS['my_records_empty'][lang])
        return

    for reg in records:
        reg_id, date, time_start, time_end, place, full_name, paid = reg
        text = f"{full_name} { {'ru':'на игру','uk':'на гру','en':'for game'}[lang] } 📅 {date} ⏰ {time_start}-{time_end} 🏟️ {place} {'✅' if paid else '❌'}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text={'ru':'Отменить запись','uk':'Скасувати запис','en':'Cancel registration'}[lang], callback_data=f'unregister_{reg_id}')]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith('unregister_'))
async def unregister(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    reg_id = int(callback.data.split('_')[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT game_id FROM registrations WHERE id = ?', (reg_id,))
        row = await cursor.fetchone()
        if row:
            game_id = row[0]
            await db.execute('DELETE FROM registrations WHERE id = ?', (reg_id,))
            await db.commit()
            cursor = await db.execute('SELECT id FROM registrations WHERE game_id = ? ORDER BY id', (game_id,))
            regs = await cursor.fetchall()
        else:
            await callback.answer(TEXTS['record_not_found'][lang])
            return
    await callback.answer(TEXTS['record_deleted'][lang])
    await callback.message.delete()

@dp.message(F.text.in_([
    '➕ Добавить игру', '➕ Додати гру', '➕ Add game'
]))
async def add_game_start(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id != ADMIN_ID:
        await message.answer(TEXTS['no_access'][lang])
        return
    add_game_states[message.from_user.id] = {'step': 'date'}
    await message.answer(TEXTS['add_game_date'][lang])

@dp.message(F.text.in_([
    '❌ Удалить игру', '❌ Видалити гру', '❌ Delete game'
]))
async def delete_game_start(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id != ADMIN_ID:
        await message.answer(TEXTS['no_access'][lang])
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id, date, time_start, time_end, place FROM games')
        games = await cursor.fetchall()
        if not games:
            await message.answer(TEXTS['delete_game_empty'][lang])
            return
        buttons = []
        for game in games:
            game_id, date, time_start, time_end, place = game
            buttons.append([InlineKeyboardButton(text=f"{date} {time_start}-{time_end} {place}", callback_data=f'delgame_{game_id}')])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(TEXTS['delete_game_choose'][lang], reply_markup=kb)

@dp.callback_query(F.data.startswith('delgame_'))
async def delete_game(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    game_id = int(callback.data.split('_')[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM games WHERE id = ?', (game_id,))
        await db.execute('DELETE FROM registrations WHERE game_id = ?', (game_id,))
        await db.commit()
    await callback.answer(TEXTS['delete_game_done'][lang])
    await callback.message.delete()

@dp.message()
async def handle_messages(message: Message):
    lang = get_lang(message.from_user.id)
    if message.from_user.id in add_game_states:
        state = add_game_states[message.from_user.id]
        step = state['step']
        if step == 'date':
            state['date'] = message.text.strip()
            state['step'] = 'time_start'
            await message.answer(TEXTS['add_game_time_start'][lang])
        elif step == 'time_start':
            state['time_start'] = message.text.strip()
            state['step'] = 'time_end'
            await message.answer(TEXTS['add_game_time_end'][lang])
        elif step == 'time_end':
            state['time_end'] = message.text.strip()
            state['step'] = 'place'
            await message.answer(TEXTS['add_game_place'][lang])
        elif step == 'place':
            state['place'] = message.text.strip()
            state['step'] = 'price'
            await message.answer(TEXTS['add_game_price'][lang])
        elif step == 'price':
            try:
                price = int(message.text.strip())
            except ValueError:
                await message.answer(TEXTS['add_game_price_error'][lang])
                return
            state['price'] = price
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('INSERT INTO games (date, time_start, time_end, place, price) VALUES (?, ?, ?, ?, ?)',
                                 (state['date'], state['time_start'], state['time_end'], state['place'], state['price']))
                await db.commit()
            await message.answer(TEXTS['add_game_added'][lang], reply_markup=reply_menu(message.from_user.id == ADMIN_ID, lang=lang))
            add_game_states.pop(message.from_user.id, None)
        return

    state = user_states.get(message.from_user.id, {})
    if 'registering' in state:
        game_id = state['registering']
        full_name = message.text.strip()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('INSERT INTO registrations (game_id, user_id, username, full_name, paid) VALUES (?, ?, ?, ?, ?)',
                             (game_id, message.from_user.id, message.from_user.username or '', full_name, 0))
            await db.commit()
        await message.answer(TEXTS['registered'][lang], reply_markup=reply_menu(message.from_user.id == ADMIN_ID, lang=lang))
        user_states[message.from_user.id].pop('registering', None)
    elif message.text and message.text.startswith('/togglepaid_'):
        if message.from_user.id != ADMIN_ID:
            await message.answer(TEXTS['no_access'][lang])
            return
        reg_id = int(message.text.split('_')[1])
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT paid FROM registrations WHERE id = ?', (reg_id,))
            row = await cursor.fetchone()
            if row is not None:
                new_paid = 0 if row[0] else 1
                await db.execute('UPDATE registrations SET paid = ? WHERE id = ?', (new_paid, reg_id))
                await db.commit()
                await message.answer(f"{TEXTS['paid_status_changed'][lang]} {'✅' if new_paid else '❌'}.")
            else:
                await message.answer(TEXTS['record_not_found'][lang])
    else:
        await message.answer(TEXTS['unknown_command'][lang], reply_markup=reply_menu(message.from_user.id == ADMIN_ID, lang=lang))

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Bot token not found. Please set the TELEGRAM_BOT_TOKEN environment variable.")
    asyncio.run(main())