import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

# ---------------------- ЗАГРУЗКА .env ----------------------
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

if not API_TOKEN:
    raise ValueError("API_TOKEN не найден в .env")

if not ADMIN_IDS_STR:
    raise ValueError("ADMIN_IDS не найден в .env")

if not GOOGLE_SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID не найден в .env")

# Преобразуем строку "1,2,3" в список int
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

# ---------------------- ЛОГИРОВАНИЕ ------------------------
logging.basicConfig(level=logging.INFO)

# ---------------------- GOOGLE SHEETS ----------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Загружаем credentials.json с ключом сервисного аккаунта
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scope)

# Авторизация и подключение к таблице по ID
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# ---------------------- НАСТРОЙКА БОТА ---------------------
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ---------------------- СОСТОЯНИЯ --------------------------
class SupportState(StatesGroup):
    consent = State()
    phone = State()
    age = State()

class AdminState(StatesGroup):
    waiting_for_broadcast_text = State()

class QuestionState(StatesGroup):
    waiting_for_question = State()

# ---------------------- ВЫДАЧА КОДОВ -----------------------
available_codes = ["83542643", "22341", "34312", "41223", "123921836", "1546523959"]
issued_codes = {}  # user_id -> code

# ---------------------- КНОПКИ -----------------------------
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Сертификат на сборную игру!", callback_data="get_code")],
            [InlineKeyboardButton(text="🔍 Показать мой код", callback_data="show_my_code")],
            [InlineKeyboardButton(text="❓ Написать в поддержку", callback_data="write_support")],
        ]
    )

def consent_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="consent_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="consent_no"),
            ]
        ]
    )

# ---------------------- КОМАНДЫ БОТА -----------------------
async def set_bot_commands(is_admin: bool, user_id: int):
    user_cmds = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="support", description="🎯 Получить сертификат на сборную игру в Bunker"),
        BotCommand(command="question", description="❓ Написать в поддержку"),
    ]

    admin_cmds = user_cmds + [
        BotCommand(command="reply", description="📩 Ответ пользователю"),
        BotCommand(command="message", description="📢 Рассылка пользователям"),
    ]

    try:
        if is_admin:
            for admin_id in ADMIN_IDS:
                await bot.set_my_commands(
                    admin_cmds,
                    scope=types.BotCommandScopeChat(chat_id=admin_id),
                )
        else:
            await bot.set_my_commands(
                user_cmds,
                scope=types.BotCommandScopeChat(chat_id=user_id),
            )
    except Exception as e:
        logging.error(f"Ошибка установки команд для пользователя {user_id}: {e}")

# ---------------------- /start -----------------------------
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await set_bot_commands(is_admin, message.from_user.id)
    text = (
        "👋 Добро пожаловать в лазертаг Bunker!\n\n"
        "Мы рады подарить вам 🎯 <b>сертификат на сборную игру</b>.\n\n"
        "🎯 <b>Получить сертификат</b> — получите персональный промокод.\n"
        "🔍 <b>Показать мой код</b> — отобразить уже выданный код.\n"
        "❓ <b>Написать в поддержку</b> — задать вопрос администраторам."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# ---------------------- /support ---------------------------
@dp.message(Command("support"))
async def support_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🛡️ Согласны ли вы на обработку персональных данных для получения сертификата "
        "на сборную игру в лазертаг Bunker?",
        reply_markup=consent_keyboard(),
    )
    await state.set_state(SupportState.consent)

# ---------------------- CONSENT ----------------------------
@dp.callback_query(F.data == "consent_yes")
async def process_consent_yes(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer("📲 Пожалуйста, отправьте свой номер телефона:", reply_markup=kb)
    await callback.answer()
    await state.set_state(SupportState.phone)

@dp.callback_query(F.data == "consent_no")
async def process_consent_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "❌ Очень жаль. Без согласия на обработку персональных данных мы не можем выдать сертификат."
    )
    await callback.message.answer("/start — начать заново")
    await callback.answer()
    await state.clear()

# ---------------------- PHONE ------------------------------
@dp.message(F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("🎂 Укажите ваш возраст:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SupportState.age)

# ---------------------- AGE + ВЫДАЧА КОДА ------------------
@dp.message(SupportState.age)
async def process_age(message: types.Message, state: FSMContext):
    age = message.text.strip()
    if not age.isdigit():
        await message.answer("⚠️ Пожалуйста, введите возраст числом.")
        return

    await state.update_data(age=age)

    user = message.from_user
    data = await state.get_data()
    phone_number = data.get("phone")

    # Проверяем, был ли уже выдан код для этого номера телефона или ID
    existing_entry = None
    try:
        cell_values = sheet.get_all_values()
        for row in cell_values:
            # row[1] = user_id, row[3] = phone_number (как в исходном коде)
            if len(row) > 3 and (row[1] == str(user.id) or row[3] == phone_number):
                existing_entry = row
                break
    except Exception as e:
        logging.error(f"Ошибка при получении данных из таблицы: {e}")

    if existing_entry:
        await message.answer(
            "❌ Вы уже получали промокод ранее. Больше одного сертификата получить нельзя."
        )
    else:
        if user.id not in issued_codes and available_codes:
            code = available_codes.pop(0)
            issued_codes[user.id] = code

            await message.answer(
                "✅ Спасибо! Ваш персональный промокод на сертификат для сборной игры в Bunker:\n\n"
                f"<code>{code}</code>"
            )

            try:
                sheet.append_row(
                    [
                        user.full_name,
                        str(user.id),
                        user.username or "нет username",
                        phone_number,
                        data.get("age"),
                        code,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
            except Exception as e:
                logging.error("Ошибка записи в таблицу: %s", e)
        else:
            await message.answer("Увы, но больше одного сертификата получить нельзя.")

    await message.answer(
        "✅ Благодарим вас за участие! Если у вас есть вопросы по лазертагу Bunker или сертификату — "
        "напишите нам, кликнув на команду /question.",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()

# ---------------------- /reply (для админа) ----------------
@dp.message(Command("reply"))
async def reply_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("⚠️ Формат: /reply USER_ID текст")
        return

    try:
        user_id = int(parts[1])
        reply_text = parts[2].strip()
        if not reply_text:
            await message.answer("❌ Текст ответа пустой.")
            return
        await bot.send_message(user_id, reply_text)
        await message.answer("✅ Ответ отправлен пользователю.")
    except Exception as e:
        logging.error("Ошибка при ответе: %s", e)
        await message.answer("❌ Не удалось отправить ответ. Проверьте ID и текст.")

# ---------------------- /message (рассылка) ----------------
@dp.message(Command("message"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    await message.answer(
        "✍️ Введите сообщение, которое хотите отправить всем пользователям, получившим промокод:"
    )
    await state.set_state(AdminState.waiting_for_broadcast_text)

@dp.message(AdminState.waiting_for_broadcast_text)
async def send_broadcast(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Сообщение не может быть пустым.")
        return

    success = 0
    failed = 0
    for user_id in issued_codes:
        try:
            await bot.send_message(user_id, text)
            success += 1
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение {user_id}: {e}")
            failed += 1

    await message.answer(f"✅ Сообщение отправлено: {success} ✅\n❌ Ошибок: {failed}")
    await state.clear()

# ---------------------- Показать код ------------------------
@dp.callback_query(F.data == "show_my_code")
async def callback_show_code(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in issued_codes:
        code = issued_codes[user_id]
        await callback_query.message.answer(
            "🔍 Ваш персональный промокод на сертификат для сборной игры в Bunker:\n\n"
            f"<code>{code}</code>"
        )
    else:
        await callback_query.message.answer(
            "ℹ️ У вас пока нет промокода. Нажмите «🎯 Сертификат на сборную игру!» чтобы получить его."
        )
    await callback_query.answer()

# ---------------------- Получить код -----------------------
@dp.callback_query(F.data == "get_code")
async def callback_get_code(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "🛡️ Согласны ли вы на обработку персональных данных для получения сертификата "
        "на сборную игру в лазертаг Bunker?",
        reply_markup=consent_keyboard(),
    )
    await state.set_state(SupportState.consent)
    await callback_query.answer()

# ---------------------- Написать в поддержку ---------------
@dp.callback_query(F.data == "write_support")
async def callback_write_support(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "❓ Пожалуйста, напишите ваш вопрос по лазертагу Bunker или сертификату, и мы скоро вам ответим!"
    )
    await state.set_state(QuestionState.waiting_for_question)
    await callback_query.answer()

@dp.message(Command("question"))
async def start_question(message: types.Message, state: FSMContext):
    await message.answer(
        "❓ Пожалуйста, напишите ваш вопрос по лазертагу Bunker или сертификату, и мы скоро вам ответим!"
    )
    await state.set_state(QuestionState.waiting_for_question)

@dp.message(QuestionState.waiting_for_question)
async def receive_question(message: types.Message, state: FSMContext):
    user = message.from_user
    question_text = message.text.strip()
    if not question_text:
        await message.answer("⚠️ Вопрос не может быть пустым.")
        return

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📩 Новый вопрос от пользователя:\n"
                f"👤 {user.full_name} (ID: <code>{user.id}</code>)\n"
                f"@{user.username or 'без username'}\n\n"
                f"❓ {question_text}",
            )
        except Exception as e:
            logging.error(f"Не удалось отправить вопрос админу {admin_id}: {e}")

    await message.answer("✅ Ваш вопрос отправлен! Спасибо, мы свяжемся с вами в ближайшее время.")
    await state.clear()

# ---------------------- Фоллбек ----------------------------
@dp.message()
async def fallback(message: types.Message):
    await message.answer("👋 Напишите /start, чтобы увидеть доступные команды.")

# ---------------------- Запуск бота ------------------------
async def main():
    logging.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
