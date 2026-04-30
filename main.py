import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# Sozlamalar (Render'da Environment Variables qismiga qo'shish tavsiya etiladi)
TOKEN = "8743222556:AAHRWt8Q6retk45JVsbR_BD7TLMR9mgyj0)M"
MONGO_URL = "mongodb+srv://rasulovdilmurodjon06_db_user:7JH3fPmxjTSasDnI@cluster0.fyhko1v.mongodb.net/?appName=Cluster0"

client = AsyncIOMotorClient(MONGO_URL)
db = client['dating_bot_db']
users_col = db['users']

bot = Bot(token=TOKEN)
dp = Dispatcher()

class Registration(StatesGroup):
    language = State()
    name = State()
    age = State()
    gender = State()
    photo = State()

# --- START VA RO'YXATDAN O'TISH ---
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇿 O'zbek"), KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇸 English")]
    ], resize_keyboard=True)
    await message.answer("Assalomu alaykum! Tilni tanlang:", reply_markup=kb)
    await state.set_state(Registration.language)

@dp.message(Registration.language)
async def set_lang(message: types.Message, state: FSMContext):
    lang = 'uz' if "O'zbek" in message.text else 'ru' if "Russ" in message.text else 'en'
    await state.update_data(lang=lang)
    await message.answer("Ismingizni kiriting:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Registration.name)

@dp.message(Registration.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(Registration.age)

@dp.message(Registration.age)
async def set_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Faqat raqam kiriting:")
    await state.update_data(age=int(message.text))
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]], resize_keyboard=True)
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.message(Registration.gender)
async def set_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await message.answer("Profilingiz uchun rasm (photo) yuboring:")
    await state.set_state(Registration.photo)

@dp.message(F.photo, Registration.photo)
async def set_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    user_data = {
        "user_id": message.from_user.id,
        "lang": data['lang'],
        "name": data['name'],
        "age": data['age'],
        "gender": data['gender'],
        "photo": photo_id
    }
    await users_col.update_one({"user_id": message.from_user.id}, {"$set": user_data}, upsert=True)
    
    main_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Qidiruv")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)
    
    await message.answer("Hammasi tayyor! Endi qidiruvni boshlashingiz mumkin.", reply_markup=main_kb)
    await state.clear()

# --- QIDIRUV VA LIKE ---
@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qizlar 👩", callback_query_data="find_Qiz")],
        [InlineKeyboardButton(text="Yigitlar 👨", callback_query_data="find_Yigit")]
    ])
    await message.answer("Kimni qidiramiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("find_"))
async def show_users(callback: types.CallbackQuery):
    target_gender = callback.data.split("_")[1]
    pipeline = [{"$match": {"gender": target_gender, "user_id": {"$ne": callback.from_user.id}}}, {"$sample": {"size": 1}}]
    cursor = users_col.aggregate(pipeline)
    profiles = await cursor.to_list(length=1)

    if profiles:
        user = profiles[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="😍 Yoqdi", callback_query_data=f"like_{user['user_id']}")],
            [InlineKeyboardButton(text="Keyingi ➡️", callback_query_data=f"find_{target_gender}")]
        ])
        await callback.message.answer_photo(user['photo'], caption=f"Ismi: {user['name']}\nYoshi: {user['age']}", reply_markup=kb)
    else:
        await callback.answer("Hozircha hech kim topilmadi.")

@dp.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(target_id, "Sizga kimdir 😍 yubordi! Profilingiz unga yoqdi.")
        await callback.answer("Xabar yuborildi!")
    except:
        await callback.answer("Xatolik!")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
