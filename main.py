import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from motor.motor_asyncio import AsyncIOMotorClient

# --- SOZLAMALAR (ENV orqali xavfsiz) ---
TOKEN = "8743222556:AAHRWt8Q6retk45JVsbR_BD7TLMR9mgyj0M"
MONGO_URL = "mongodb+srv://rasulovdilmurodjon06_db_user:7JH3fPmxjTSasDnI@cluster0.fyhko1v.mongodb.net/?appName=Cluster0"

client = AsyncIOMotorClient(MONGO_URL)
db = client['dating_bot_db']
users_col = db['users']

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot is Live!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(
        runner,
        '0.0.0.0',
        int(os.environ.get("PORT", 8080))
    ).start()

# --- HOLATLAR ---
class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    photo = State()

# --- MENU ---
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="⚙️ Sozlamalar")]
        ],
        resize_keyboard=True
    )

# --- START ---
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user:
        await message.answer("Xush kelibsiz!", reply_markup=main_menu())
    else:
        await message.answer("Ismingizni kiriting:")
        await state.set_state(Registration.name)

# --- NAME ---
@dp.message(Registration.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(Registration.age)

# --- AGE ---
@dp.message(Registration.age)
async def set_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Iltimos faqat raqam kiriting")

    await state.update_data(age=int(message.text))

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]],
        resize_keyboard=True
    )

    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.gender)

# --- GENDER ---
@dp.message(Registration.gender)
async def set_gender(message: types.Message, state: FSMContext):
    if message.text not in ["Yigit", "Qiz"]:
        return await message.answer("Faqat tugmadan tanlang!")

    await state.update_data(gender=message.text)
    await message.answer("Rasm yuboring 📸")
    await state.set_state(Registration.photo)

# --- PHOTO ---
@dp.message(F.photo, Registration.photo)
async def set_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()

    user_doc = {
        "user_id": message.from_user.id,
        "name": data['name'],
        "age": data['age'],
        "gender": data['gender'],
        "photo": message.photo[-1].file_id
    }

    await users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": user_doc},
        upsert=True
    )

    await state.clear()
    await message.answer("Ro'yxatdan o'tdingiz!", reply_markup=main_menu())

# --- AGAR RASM YUBORMASA ---
@dp.message(Registration.photo)
async def photo_error(message: types.Message):
    await message.answer("Iltimos rasm yuboring 📸")

# --- QIDIRUV ---
@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Qizlar 👩", callback_data="find_Qiz")],
            [InlineKeyboardButton(text="Yigitlar 👨", callback_data="find_Yigit")]
        ]
    )
    await message.answer("Kimni qidiramiz?", reply_markup=kb)

# --- USER KO'RSATISH ---
@dp.callback_query(F.data.startswith("find_"))
async def show_users(callback: types.CallbackQuery):
    target_gender = callback.data.split("_")[1]

    pipeline = [
        {"$match": {
            "gender": target_gender,
            "user_id": {"$ne": callback.from_user.id}
        }},
        {"$sample": {"size": 1}}
    ]

    profiles = await users_col.aggregate(pipeline).to_list(length=1)

    if profiles:
        user = profiles[0]

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="😍 Yoqdi", callback_data=f"like_{user['user_id']}")],
                [InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"find_{target_gender}")]
            ]
        )

        await callback.message.delete()

        await callback.message.answer_photo(
            user['photo'],
            caption=f"Ismi: {user['name']}\nYoshi: {user['age']}",
            reply_markup=kb
        )
    else:
        await callback.answer("Hozircha hech kim yo'q", show_alert=True)

# --- LIKE ---
@dp.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    try:
        target_id = int(callback.data.split("_")[1])

        await bot.send_message(
            target_id,
            "Sizga kimdir 😍 like bosdi!"
        )

        await callback.answer("Yuborildi!", show_alert=True)

    except Exception as e:
        print(e)
        await callback.answer("Xatolik yuz berdi")

# --- PROFIL ---
@dp.message(F.text == "👤 Profilim")
async def my_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})

    if user:
        await message.answer_photo(
            user['photo'],
            caption=f"Ism: {user['name']}\nYosh: {user['age']}\nJins: {user['gender']}"
        )

# --- SOZLAMALAR ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Profilni o'chirish", callback_data="del_profile")]
        ]
    )
    await message.answer("Sozlamalar:", reply_markup=kb)

# --- DELETE ---
@dp.callback_query(F.data == "del_profile")
async def delete_profile(callback: types.CallbackQuery):
    await users_col.delete_one({"user_id": callback.from_user.id})

    await callback.message.answer(
        "Profil o'chirildi. /start bosing",
        reply_markup=ReplyKeyboardRemove()
    )

    await callback.answer("O'chirildi")

# --- MAIN ---
async def main():
    logging.basicConfig(level=logging.INFO)

    await start_web_server()

    # polling (agar webhook qilmasang)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
