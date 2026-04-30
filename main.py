import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import *
from motor.motor_asyncio import AsyncIOMotorClient

# ================== SOZLAMALAR ==================
TOKEN = "8743222556:AAHRWt8Q6retk45JVsbR_BD7TLMR9mgyj0M"
MONGO_URL = "mongodb+srv://rasulovdilmurodjon06_db_user:7JH3fPmxjTSasDnI@cluster0.fyhko1v.mongodb.net/?appName=Cluster0"

ADMIN_ID = 123456789  # 👈 o'zingni ID yoz

client = AsyncIOMotorClient(MONGO_URL)
db = client['dating_bot_db']
users_col = db['users']

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== CHAT STATE =====
active_reply = {}

# ===== REG STATES =====
class Reg(StatesGroup):
    name = State()
    age = State()
    gender = State()
    region = State()
    city = State()
    photo = State()

# ===== REGION =====
REGIONS = {
    "Toshkent": ["Chilonzor", "Yunusobod"],
    "Farg'ona": ["Qo'qon", "Marg'ilon"]
}

# ===== MENU =====
def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="👤 Profilim")],
            [KeyboardButton(text="📞 Admin")]
        ],
        resize_keyboard=True
    )

# ===== BAN CHECK FUNCTION =====
async def is_banned(user_id: int):
    user = await users_col.find_one({"user_id": user_id})
    return user and user.get("banned") == True

# ================= START =================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):

    if await is_banned(message.from_user.id):
        return await message.answer("🚫 Siz bloklangansiz")

    user = await users_col.find_one({"user_id": message.from_user.id})

    if user:
        await message.answer("Xush kelibsiz!", reply_markup=menu())
    else:
        await message.answer("Ismingiz:")
        await state.set_state(Reg.name)

# ================= REG =================
@dp.message(Reg.name)
async def name(m: types.Message, s: FSMContext):
    await s.update_data(name=m.text)
    await m.answer("Yosh:")
    await s.set_state(Reg.age)

@dp.message(Reg.age)
async def age(m: types.Message, s: FSMContext):
    if not m.text.isdigit():
        return await m.answer("Raqam kiriting")

    await s.update_data(age=int(m.text))

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]],
        resize_keyboard=True
    )

    await m.answer("Jins:", reply_markup=kb)
    await s.set_state(Reg.gender)

@dp.message(Reg.gender)
async def gender(m: types.Message, s: FSMContext):
    await s.update_data(gender=m.text)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=r)] for r in REGIONS],
        resize_keyboard=True
    )

    await m.answer("Viloyat:", reply_markup=kb)
    await s.set_state(Reg.region)

@dp.message(Reg.region)
async def region(m: types.Message, s: FSMContext):
    await s.update_data(region=m.text)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c)] for c in REGIONS[m.text]],
        resize_keyboard=True
    )

    await m.answer("Shahar:", reply_markup=kb)
    await s.set_state(Reg.city)

@dp.message(Reg.city)
async def city(m: types.Message, s: FSMContext):
    await s.update_data(city=m.text)
    await m.answer("Rasm yuboring")
    await s.set_state(Reg.photo)

@dp.message(F.photo, Reg.photo)
async def photo(m: types.Message, s: FSMContext):

    data = await s.get_data()

    user = {
        "user_id": m.from_user.id,
        "name": data['name'],
        "age": data['age'],
        "gender": data['gender'],
        "region": data['region'],
        "city": data['city'],
        "photo": m.photo[-1].file_id,
        "banned": False
    }

    await users_col.update_one(
        {"user_id": user["user_id"]},
        {"$set": user},
        upsert=True
    )

    await s.clear()
    await m.answer("Tayyor!", reply_markup=menu())

# ================= SEARCH =================
@dp.message(F.text == "🔍 Qidiruv")
async def search(m: types.Message):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Qizlar", callback_data="find_Qiz")],
            [InlineKeyboardButton(text="Yigitlar", callback_data="find_Yigit")]
        ]
    )

    await m.answer("Tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("find_"))
async def find(c: types.CallbackQuery):

    if await is_banned(c.from_user.id):
        return await c.answer("🚫 bloklangan")

    gender = c.data.split("_")[1]

    user = await users_col.aggregate([
        {"$match": {"gender": gender, "user_id": {"$ne": c.from_user.id}}},
        {"$sample": {"size": 1}}
    ]).to_list(1)

    if not user:
        return await c.answer("Yo‘q")

    u = user[0]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Xabar", callback_data=f"msg_{u['user_id']}")],
            [InlineKeyboardButton(text="Keyingi", callback_data=f"find_{gender}")]
        ]
    )

    await c.message.answer_photo(
        u['photo'],
        caption=f"{u['name']} | {u['age']}",
        reply_markup=kb
    )

# ================= CHAT =================
@dp.callback_query(F.data.startswith("msg_"))
async def msg_start(c: types.CallbackQuery):
    active_reply[c.from_user.id] = int(c.data.split("_")[1])
    await c.message.answer("Xabar yozing")
    await c.answer()

@dp.message()
async def chat(m: types.Message):

    if await is_banned(m.from_user.id):
        return

    uid = m.from_user.id

    if uid in active_reply:

        target = active_reply[uid]

        await bot.send_message(
            target,
            f"📩 Xabar:\n{m.text}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ Javob", callback_data=f"reply_{uid}")]
                ]
            )
        )

        await m.answer("Yuborildi")
        del active_reply[uid]

@dp.callback_query(F.data.startswith("reply_"))
async def reply(c: types.CallbackQuery):
    active_reply[c.from_user.id] = int(c.data.split("_")[1])
    await c.message.answer("Javob yozing")
    await c.answer()

# ================= PROFILE =================
@dp.message(F.text == "👤 Profilim")
async def profile(m: types.Message):

    if await is_banned(m.from_user.id):
        return

    user = await users_col.find_one({"user_id": m.from_user.id})

    if user:
        await m.answer_photo(
            user['photo'],
            caption=f"{user['name']} | {user['age']}\n{user['region']} - {user['city']}"
        )

# ================= ADMIN =================
@dp.message(Command("stat"))
async def stat(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return

    total = await users_col.count_documents({})
    boys = await users_col.count_documents({"gender": "Yigit"})
    girls = await users_col.count_documents({"gender": "Qiz"})

    await m.answer(
        f"📊 Statistika\n\n👥 {total}\n👨 {boys}\n👩 {girls}"
    )

@dp.message(Command("ban"))
async def ban(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return

    try:
        uid = int(m.text.split()[1])

        await users_col.update_one(
            {"user_id": uid},
            {"$set": {"banned": True}}
        )

        await m.answer("🚫 ban qilindi")
    except:
        await m.answer("xato")

@dp.message(Command("unban"))
async def unban(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return

    try:
        uid = int(m.text.split()[1])

        await users_col.update_one(
            {"user_id": uid},
            {"$set": {"banned": False}}
        )

        await m.answer("✅ ochildi")
    except:
        await m.answer("xato")

# ================= RUN =================
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
