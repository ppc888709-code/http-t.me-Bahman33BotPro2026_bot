from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, func, desc
import secrets, html
from config import settings
from db import init_db, SessionLocal
from models import Business, CatalogItem, Customer, Orde
FastAPI(title="Business Bot Pro Admin")
security = HTTPBasic()

def auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    ok_pass = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="ورود نامعتبر", headers={"WWW-Authenticate": "Basic"})
    return True

def page(body):
    return """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Business Bot Pro</title><style>
    body{font-family:Tahoma,Arial;background:#f4f6fa;margin:0;color:#182230}.wrap{max-width:1100px;margin:28px auto;padding:16px}
    .card{background:white;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 3px 14px #17255410}
    input,textarea,select{padding:10px;border:1px solid #ccd3df;border-radius:8px;margin:5px;max-width:95%}button{background:#155eef;color:white;border:0;padding:10px 16px;border-radius:8px;cursor:pointer}
  table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #e5e7eb;text-align:right}small{color:#667085}
    </style><div class="wrap"><h2>Business Bot Pro</h2><small>پنل مدیریت چندکسب‌وکاره</small>""" + body + "</div></html>"

on_event("startup")
def startup():
    init_db()

get("/", response_class=HTMLResponse)
def dashboard(_: bool = Depends(auth)):
    with SessionLocal() as db:
        businesses = db.scalars(select(Business).order_by(Business.id.desc())).all()
        total_customers = db.scalar(select(func.count(Customer.id))) or 0
        total_orders = db.scalar(select(func.count(Order.id))) or 0
        rows = "".join(f"<tr><td>{b.id}</td><td>{html.escape(b.name)}</td><td>{html.escape(b.slug)}</td><td>{'فعال' if b.is_active else 'غیرفعال'}</td><td><a href='/business/{b.id}'>مدیریت</a></td></tr>" for b in businesses)
    body = f"""<div class='card'><b>خلاصه</b><p>مشتریان: {total_customers} | درخواست‌ها: {total_orders}</p></div>
    <div class='card'><h3>افزودن کسب‌وکار</h3><form method='post' action='/business/add'>
    <input name='name' placeholder='نام کسب‌وکار' required><input name='slug' placeholder='شناسه انگلیسی یکتا مثل panahnoor' required>
    <input name='admin_ids' placeholder='شناسه مدیران تلگرام، با کاما جدا شود'><br><textarea name='description' placeholder='توضیحات و اطلاعات پاسخ‌گویی هوش مصنوعی'></textarea><button>ثبت کسب‌وکار</button></form></div>
    <div class='card'><h3>کسب‌وکارها</h3><table><tr><th>ID</th><th>نام</th><th>شناسه</th><th>وضعیت</th><th>عملیات</th></tr>{rows}</table></div>
    <div class='card'><a href='/orders'>مشاهده همه درخواست‌ها</a></div>"""
    return page(body)

post("/business/add")
def add_business(name: str = Form(...), slug: str = Form(...), admin_ids: str = Form(""), description: str = Form(""), _: bool = Depends(auth)):
    with SessionLocal() as db:
        slug = slug.strip().lower()
        if db.scalar(select(Business).where(Business.slug == slug)):
            raise HTTPException(400, "شناسه تکراری است")
        db.add(Business(name=name.strip(), slug=slug, admin_ids=admin_ids, description=description))
        db.commit()
    return RedirectResponse("/", status_code=303)

get("/business/{bid}", response_class=HTMLResponse)
def business_detail(bid: int, _: bool = Depends(auth)):
    with SessionLocal() as db:
        b = db.get(Business, bid)
        if not b:
            raise HTTPException(404, "یافت نشد")
        items = db.scalars(select(CatalogItem).where(CatalogItem.business_id == bid)).all()
        item_rows = "".join(f"<tr><td>{html.escape(i.title)}</td><td>{i.kind}</td><td>{html.escape(i.price_text)}</td><td>{'فعال' if i.is_active else 'غیرفعال'}</td></tr>" for i in items)
        body = f"""<div class='card'><h3>{html.escape(b.name)}</h3><p>شناسه: {html.escape(b.slug)}</p>
        <form method='post' action='/business/{bid}/update'><input name='admin_ids' value='{html.escape(b.admin_ids or '')}' placeholder='شناسه مدیران'>
        <textarea name='description'>{html.escape(b.description or '')}</textarea><button>ذخیره تنظیمات</button></form></div>
        <div class='card'><h3>افزودن محصول یا خدمت</h3><form method='post' action='/business/{bid}/item'>
        <input name='title' placeholder='نام محصول/خدمت' required><select name='kind'><option value='service'>خدمت</option><option value='product'>محصول</option></select>
        <input name='price_text' placeholder='قیمت یا عبارت استعلام قیمت'><br><textarea name='description' placeholder='توضیحات'></textarea><button>افزودن</button></form></div>
        <div class='card'><h3>فهرست</h3><table><tr><th>نام</th><th>نوع</th><th>قیمت</th><th>وضعیت</th></tr>{item_rows}</table></div>
        <div class='card'><a href='/orders?business_id={bid}'>درخواست‌های این کسب‌وکار</a> | <a href='/'>بازگشت</a></div>"""
    return page(body)

post("/business/{bid}/update")
def update_business(bid: int, admin_ids: str = Form(""), description: str = Form(""), _: bool = Depends(auth)):
    with SessionLocal() as db:
        b = db.get(Business, bid)
        if not b:
            raise HTTPException(404)
        b.admin_ids = admin_ids
        b.description = description
        db.commit()
    return RedirectResponse(f"/business/{bid}", status_code=303)

post("/business/{bid}/item")
def add_item(bid: int, title: str = Form(...), kind: str = Form("service"), price_text: str = Form("استعلام قیمت"), description: str = Form(""), _: bool = Depends(auth)):
    with SessionLocal() as db:
        if not db.get(Business, bid):
            raise HTTPException(404)
        db.add(CatalogItem(business_id=bid, title=title, kind=kind, price_text=price_text, description=description))
        db.commit()
    return RedirectResponse(f"/business/{bid}", status_code=303)

get("/orders", response_class=HTMLResponse)
def orders(business_id: int | None = None, _: bool = Depends(auth)):
    with SessionLocal() as db:
        stmt = select(Order).order_by(desc(Order.id))
        if business_id:
            stmt = stmt.where(Order.business_id == business_id)
        data = db.scalars(stmt.limit(300)).all()
        rows = []
        for order in data:
            customer = db.get(Customer, order.customer_id)
            business = db.get(Business, order.business_id)
            rows.append(f"<tr><td>#{order.id}</td><td>{html.escape(business.name if business else '')}</td><td>{html.escape(customer.full_name if customer else '')}</td><td>{html.escape(customer.phone if customer else '')}</td><td>{html.escape(order.details)}</td><td>{order.status}</td></tr>")
    body = "<div class='card'><h3>درخواست‌ها (۳۰۰ مورد اخیر)</h3><table><tr><th>شماره</th><th>کسب‌وکار</th><th>مشتری</th><th>تماس</th><th>درخواست</th><th>وضعیت</th></tr>" + "".join(rows) + "</table><p><a href='/'>بازگشت</a></p></div>"
    return page(body)
