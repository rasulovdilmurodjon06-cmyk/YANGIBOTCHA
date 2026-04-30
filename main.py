import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- SOZLAMALAR ---
TOKEN = "8743222556:AAHRWt8Q6retk45JVsbR_BD7TLMR9mgyj0M"
MONGO_URL = "mongodb+srv://rasulovdilmurodjon06_db_user:7JH3fPmxjTSasDnI@cluster0.fyhko1v.mongodb.net/?appName=Cluster0"

# MongoDB ulanishi
client = AsyncIOMotorClient(MONGO_URL)
db = client['dating_bot_db']
users_col = db['users']

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- RENDER UCHUN VEB-SERVER (O'CHIB QOLMASLIGI UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- HOLATLAR (STATES) ---
class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    photo = State()

# --- KLAVIATURALAR ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Qidiruv")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

# --- BOT BUYRUQLARI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user:
        await message.answer("Xush kelibsiz! Tanishuvni boshlaymiz.", reply_markup=main_menu())
    else:
        await message.answer("Assalomu alaykum! Tanishuv botiga xush kelibsiz.\nRo'yxatdan o'tish uchun ismingizni kiriting:")
        await state.set_state(Registration.name)

# --- RO'YXATDAN O'TISH JARAYONI ---
@dp.message(Registration.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(Registration.age)

@dp.message(Registration.age)
async def set_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Iltimos, yoshingizni raqamda kiriting:")
    await state.update_data(age=int(message.text))
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]], resize_keyboard=True)
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.message(Registration.gender)
async def set_gender(message: types.Message, state: FSMContext):
    if message.text not in ["Yigit", "Qiz"]:
        return await message.answer("Tugmalardan birini tanlang:")
    await state.update_data(gender=message.text)
    await message.answer("Profilingiz uchun bitta rasm yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Registration.photo)

@dp.message(F.photo, Registration.photo)
async def set_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    user_data = {
        "user_id": message.from_user.id,
        "name": data['name'],
        "age": data['age'],
        "gender": data['gender'],
        "photo": photo_id
    }
    await users_col.update_one({"user_id": message.from_user.id}, {"$set": user_data}, upsert=True)
    
    await message.answer("Tabriklaymiz! Ro'yxatdan muvaffaqiyatli o'tdingiz.", reply_markup=main_menu())
    await state.clear()

# --- ASOSIY MENYULAR ---
@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qizlar 👩", callback_query_data="find_Qiz")],
        [InlineKeyboardButton(text="Yigitlar 👨", callback_query_data="find_Yigit")]
    ])
    await message.answer("Kimni qidiramiz?", reply_markup=kb)

@dp.message(F.text == "👤 Profilim")
async def show_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user:
        caption = f"Sizning profilingiz:\n\nIsm: {user['name']}\nYosh: {user['age']}\nJins: {user['gender']}"
        await message.answer_photo(user['photo'], caption=caption)
    else:
        await message.answer("Profilingiz topilmadi. /start bosing.")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings(message: types.Message):
    await message.answer("Sozlamalar bo'limi tez kunda ishga tushadi.")

# --- CALLBACK QUERY (QIDIRUV LOGIKASI) ---
@dp.callback_query(F.data.startswith("find_"))
async def show_users(callback: types.CallbackQuery):
    target_gender = callback.data.split("_")[1]
    # Tasodifiy bir foydalanuvchini olish (o'zidan tashqari)
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
        await callback.answer()
    else:
        await callback.answer("Hozircha hech kim topilmadi.", show_alert=True)

@dp.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(target_id, "Sizga kimdir 😍 yubordi! Profilingiz unga yoqdi.")
        await callback.answer("Xabar yuborildi!", show_alert=True)
    except:
        await callback.answer("Xabar yuborishda xatolik (foydalanuvchi botni bloklagan bo'lishi mumkin).")

# --- ASOSIY ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
