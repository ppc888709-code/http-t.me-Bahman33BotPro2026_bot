import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from .config import BOT_TOKEN, ADMIN_IDS, BUSINESS_NAME
from .db import init_db, list_businesses, get_business, save_customer, create_order
from .ai_helper import answer_question

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('business_bot')

class OrderFlow(StatesGroup):
    business = State()
    name = State()
    phone = State()
    details = State()

main_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🛍 ثبت سفارش / استعلام قیمت')],
    [KeyboardButton(text='ℹ️ راهنمایی'), KeyboardButton(text='☎️ ارتباط با مدیر')]
], resize_keyboard=True)

async def start(message: Message):
    businesses = list_businesses()
    if not businesses:
        await message.answer('در حال حاضر کسب‌وکاری برای انتخاب فعال نیست. لطفاً بعداً مراجعه کنید.')
        return
    lines = [f'سلام {message.from_user.first_name or "دوست عزیز"} 🌷', 'به سامانه خوش آمدید.', '', 'برای ثبت سفارش از دکمه زیر استفاده کنید.']
    await message.answer('\n'.join(lines), reply_markup=main_keyboard)

async def begin_order(message: Message, state: FSMContext):
    businesses = list_businesses()
    if not businesses:
        await message.answer('فعلاً کسب‌وکار فعالی ثبت نشده است.')
        return
    if len(businesses) == 1:
        await state.update_data(business_id=businesses[0]['id'], business_name=businesses[0]['name'])
        await state.set_state(OrderFlow.name)
        await message.answer('نام و نام خانوادگی خود را بنویسید:', reply_markup=ReplyKeyboardRemove())
    else:
        buttons = [[KeyboardButton(text=f"{b['id']} - {b['name']}")] for b in businesses]
        await state.set_state(OrderFlow.business)
        await message.answer('نام کسب‌وکار موردنظر را انتخاب کنید:', reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True))

async def choose_business(message: Message, state: FSMContext):
    try:
        business_id = int(message.text.split('-', 1)[0].strip())
    except (ValueError, AttributeError):
        await message.answer('لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید.')
        return
    business = get_business(business_id)
    if not business:
        await message.answer('این گزینه معتبر نیست. دوباره انتخاب کنید.')
        return
    await state.update_data(business_id=business_id, business_name=business['name'])
    await state.set_state(OrderFlow.name)
    await message.answer('نام و نام خانوادگی خود را بنویسید:', reply_markup=ReplyKeyboardRemove())

async def receive_name(message: Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 2:
        await message.answer('لطفاً نام خود را وارد کنید.')
        return
    await state.update_data(customer_name=message.text.strip())
    await state.set_state(OrderFlow.phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='ارسال شماره تماس', request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer('شماره تماس خود را ارسال کنید یا به صورت متن بنویسید:', reply_markup=kb)

async def receive_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or '').strip()
    if len(phone) < 7:
        await message.answer('شماره تماس معتبر وارد کنید.')
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderFlow.details)
    await message.answer('شرح سفارش یا کالای موردنظر را بنویسید:', reply_markup=ReplyKeyboardRemove())

async def receive_details(message: Message, state: FSMContext, bot: Bot):
    details = (message.text or '').strip()
    if len(details) < 3:
        await message.answer('لطفاً توضیحات سفارش را کامل‌تر بنویسید.')
        return
    data = await state.get_data()
    order_id = create_order(data['business_id'], message.from_user.id, data['customer_name'], data['phone'], details)
    save_customer(message.from_user.id, data['customer_name'], data['phone'])
    note = (f'🆕 سفارش جدید شماره {order_id}\nکسب‌وکار: {data["business_name"]}\n'
            f'نام: {data["customer_name"]}\nتلفن: {data["phone"]}\n'
            f'شناسه تلگرام: {message.from_user.id}\nشرح: {details}')
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, note)
        except Exception as exc:
            log.warning('Could not notify administrator %s: %s', admin_id, exc)
    await state.clear()
    await message.answer(f'درخواست شما با شماره {order_id} ثبت شد. مدیر برای پیگیری با شما تماس می‌گیرد. 🌷', reply_markup=main_keyboard)

async def help_user(message: Message):
    answer = await answer_question(message.text or 'راهنمایی')
    await message.answer(answer, reply_markup=main_keyboard)

async def main():
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN is missing. Set it in the service environment variables.')
    init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(start, CommandStart())
    dp.message.register(begin_order, F.text == '🛍 ثبت سفارش / استعلام قیمت')
    dp.message.register(help_user, F.text.in_({'ℹ️ راهنمایی', '☎️ ارتباط با مدیر'}))
    dp.message.register(choose_business, OrderFlow.business)
    dp.message.register(receive_name, OrderFlow.name)
    dp.message.register(receive_phone, OrderFlow.phone)
    dp.message.register(receive_details, OrderFlow.details)
    dp.message.register(help_user, Command('help'))
    log.info('Bot polling started')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
