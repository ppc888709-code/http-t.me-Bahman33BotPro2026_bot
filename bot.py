import asyncio, logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from config import settings
from db import init_db, SessionLocal
from models import Business, Customer, CatalogItem, Order, ConversationMessage
from ai import answer_question

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

class Flow(StatesGroup):
    name = State()
    phone = State()
    request_details = State()
    ask_ai = State()

def get_business(bid):
    with SessionLocal() as db:
        return db.get(Business, bid)

def business_keyboard():
    with SessionLocal() as db:
        businesses = db.scalars(select(Business).where(Business.is_active == True).order_by(Business.name)).all()
        rows = [[InlineKeyboardButton(text=b.name, callback_data=f"biz:{b.id}")] for b in businesses]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

def main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛍 محصولات و خدمات"), KeyboardButton(text="📝 ثبت درخواست قیمت")],
        [KeyboardButton(text="🤖 پرسش از دستیار"), KeyboardButton(text="☎️ اطلاعات تماس")]
    ], resize_keyboard=True)

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    kb = business_keyboard()
    if not kb:
        await message.answer("هنوز کسب‌وکاری تعریف نشده است. مدیر باید ابتدا از پنل مدیریت، کسب‌وکار اضافه کند.")
        return
    await message.answer("سلام! به Business Bot Pro خوش آمدید. کسب‌وکار موردنظر را انتخاب کنید:", reply_markup=kb)

@dp.callback_query(F.data.startswith("biz:"))
async def choose_business(call: CallbackQuery, state: FSMContext):
    bid = int(call.data.split(":")[1])
    b = get_business(bid)
    if not b or not b.is_active:
        await call.answer("این کسب‌وکار در دسترس نیست.", show_alert=True)
        return
    await state.clear()
    await state.update_data(business_id=bid)
    await call.message.answer(f"به «{b.name}» خوش آمدید. برای ثبت سفارش، ابتدا نام و شماره تماس خود را ثبت کنید.", reply_markup=main_keyboard())
    await call.answer()

async def ensure_customer(message: Message, state: FSMContext):
    data = await state.get_data()
    bid = data.get("business_id")
    if not bid:
        await message.answer("ابتدا /start را بزنید و کسب‌وکار را انتخاب کنید.")
        return False
    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.business_id == bid, Customer.telegram_id == message.from_user.id))
        if customer and customer.phone:
            return True
    await state.set_state(Flow.name)
    await message.answer("لطفاً نام و نام خانوادگی خود را بنویسید:")
    return False

@dp.message(Flow.name)
async def save_name(message: Message, state: FSMContext):
    await state.update_data(full_name=(message.text or "")[:160])
    await state.set_state(Flow.phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 ارسال شماره تماس", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("برای ادامه، شماره تماس خود را با دکمه زیر به اشتراک بگذارید:", reply_markup=kb)

@dp.message(Flow.phone, F.contact)
async def save_phone(message: Message, state: FSMContext):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("لطفاً شماره تماس متعلق به خودتان را ارسال کنید.")
        return
    data = await state.get_data()
    bid = data["business_id"]
    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.business_id == bid, Customer.telegram_id == message.from_user.id))
        if not customer:
            customer = Customer(business_id=bid, telegram_id=message.from_user.id)
            db.add(customer)
        customer.full_name = data.get("full_name", "")
        customer.phone = message.contact.phone_number
        customer.username = message.from_user.username or ""
        db.commit()
    await state.clear()
    await state.update_data(business_id=bid)
    await message.answer("اطلاعات شما ثبت شد. از منوی زیر استفاده کنید.", reply_markup=main_keyboard())

@dp.message(F.text == "🛍 محصولات و خدمات")
async def catalog(message: Message, state: FSMContext):
    bid = (await state.get_data()).get("business_id")
    if not bid:
        await message.answer("ابتدا /start را بزنید.")
        return
    with SessionLocal() as db:
        items = db.scalars(select(CatalogItem).where(CatalogItem.business_id == bid, CatalogItem.is_active == True)).all()
        output = [(i.title, i.description, i.price_text) for i in items]
    if not output:
        await message.answer("هنوز محصول یا خدمتی ثبت نشده است.")
        return
    for title, description, price in output:
        await message.answer(f"<b>{title}</b>\n{description}\nقیمت: {price}", parse_mode="HTML")

@dp.message(F.text == "📝 ثبت درخواست قیمت")
async def new_request(message: Message, state: FSMContext):
    if not await ensure_customer(message, state):
        return
    await state.set_state(Flow.request_details)
    await message.answer("درخواست خود را بنویسید؛ نام محصول/خدمت، تعداد، شهر و توضیحات لازم را ذکر کنید.")

@dp.message(Flow.request_details)
async def save_request(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    bid = data["business_id"]
    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.business_id == bid, Customer.telegram_id == message.from_user.id))
        if not customer:
            await message.answer("ابتدا اطلاعات تماس را ثبت کنید.")
            await state.clear()
            return
        order = Order(business_id=bid, customer_id=customer.id, request_type="quote", details=(message.text or "")[:4000])
        db.add(order)
        db.commit()
        oid = order.id
        business = db.get(Business, bid)
        admins = [x.strip() for x in (business.admin_ids or "").split(",") if x.strip()]
        note = f"🔔 درخواست جدید #{oid}\nکسب‌وکار: {business.name}\nمشتری: {customer.full_name}\nتماس: {customer.phone}\nمتن: {order.details}"
    for admin_id in admins:
        try:
            await bot.send_message(int(admin_id), note)
        except Exception:
            logging.exception("Admin notification failed")
    await state.clear()
    await state.update_data(business_id=bid)
    await message.answer(f"درخواست شما با شماره پیگیری {oid} ثبت شد.", reply_markup=main_keyboard())

@dp.message(F.text == "🤖 پرسش از دستیار")
async def ask_start(message: Message, state: FSMContext):
    if not await ensure_customer(message, state):
        return
    await state.set_state(Flow.ask_ai)
    await message.answer("سؤال خود را بنویسید. پاسخ بر اساس اطلاعات ثبت‌شده کسب‌وکار ارائه می‌شود.")

@dp.message(Flow.ask_ai)
async def ask_ai(message: Message, state: FSMContext):
    data = await state.get_data()
    bid = data["business_id"]
    business = get_business(bid)
    question = (message.text or "")[:2000]
    answer = await answer_question(business.name, business.description, question)
    with SessionLocal() as db:
        db.add(ConversationMessage(business_id=bid, telegram_id=message.from_user.id, role="user", content=question))
        db.add(ConversationMessage(business_id=bid, telegram_id=message.from_user.id, role="assistant", content=answer))
        db.commit()
    await message.answer(answer, reply_markup=main_keyboard())
    await state.clear()
    await state.update_data(business_id=bid)

@dp.message(F.text == "☎️ اطلاعات تماس")
async def contact_info(message: Message, state: FSMContext):
    bid = (await state.get_data()).get("business_id")
    business = get_business(bid) if bid else None
    if not business:
        await message.answer("ابتدا کسب‌وکار را انتخاب کنید.")
        return
    await message.answer(f"{business.name}\n{business.description or 'برای اطلاعات بیشتر درخواست ثبت کنید.'}")

async def main():
    if not settings.BOT_TOKEN or "PASTE_" in settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN را در فایل .env تنظیم کنید.")
    init_db()
    bot = Bot(settings.BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
