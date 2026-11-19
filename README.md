# Business Bot Pro — نسخه بازسازی‌شده

ربات تلگرام چندکسب‌وکاره برای ثبت مشتری، دریافت شماره تماس، ثبت سفارش و استعلام قیمت، اعلان به مدیر و پنل مدیریتی وب.

## ساختار پروژه

- `botcore/` کد اصلی ربات و پنل
- `botcore/bot.py` اجرای ربات تلگرام
- `botcore/admin.py` پنل مدیریتی وب
- `botcore/db.py` پایگاه داده SQLite
- `.env.example` نمونه متغیرهای محیطی؛ توکن واقعی را اینجا ننویسید
- `render.yaml` الگوی استقرار Render

## اجرای محلی

1. Python 3.11 یا جدیدتر نصب کنید.
2. `pip install -r requirements.txt`
3. از `.env.example` یک فایل با نام `.env` بسازید و مقدارهای واقعی را فقط در همان فایل وارد کنید.
4. ربات: `python -m botcore.bot`
5. پنل: `uvicorn botcore.admin:api --host 0.0.0.0 --port 8000`

## تنظیم Render

برای Worker:
- Root Directory: خالی
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m botcore.bot`

برای پنل وب یک Web Service جدا بسازید:
- Root Directory: خالی
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn botcore.admin:api --host 0.0.0.0 --port $PORT`

متغیرهای محیطی ضروری Worker: `BOT_TOKEN`, `ADMIN_IDS`, `DATABASE_PATH`.
متغیرهای پنل: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DATABASE_PATH`.
`ADMIN_IDS` فهرست شناسه عددی مدیران تلگرام با جداکننده ویرگول است.

## پایداری داده

SQLite روی فضای موقت میزبان ممکن است پس از راه‌اندازی مجدد پاک شود. برای نگهداری داده‌ها یک دیسک پایدار متصل کنید و `DATABASE_PATH=/var/data/business_bot.sqlite3` قرار دهید. فایل `render.yaml` نمونه دیسک پایدار را نشان می‌دهد؛ قبل از استفاده، هزینه و پشتیبانی پلن Render را بررسی کنید. برای اجرای دو سرویس روی یک فایل SQLite، هر دو باید به همان فضای پایدار مشترک دسترسی داشته باشند؛ در غیر این صورت از PostgreSQL استفاده کنید.

## امنیت

- هرگز فایل `.env`، توکن تلگرام یا رمز پنل را در GitHub بارگذاری نکنید.
- مخزن را ترجیحاً Private بسازید.
- برای پنل، رمز طولانی و یکتا تنظیم کنید.
- فقط شناسه عددی مدیران مورد اعتماد را در `ADMIN_IDS` قرار دهید.
- قبل از استفاده تجاری، سفارش آزمایشی و دریافت اعلان مدیر را تست کنید.

## نکته نسخه

این نسخه یک پایه اجرایی بازسازی‌شده است؛ پیش از استفاده واقعی باید روی حساب و پلن میزبانی شما Deploy و از نظر دریافت پیام، ذخیره سفارش، اعلان مدیر و ماندگاری پایگاه داده آزمایش شود.
