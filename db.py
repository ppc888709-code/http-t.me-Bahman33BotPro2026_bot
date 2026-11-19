import sqlite3
from contextlib import contextmanager
from .config import DATABASE_PATH

@contextmanager
def connect():
    db = sqlite3.connect(DATABASE_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS businesses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          description TEXT DEFAULT '',
          contact_phone TEXT DEFAULT '',
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS customers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          telegram_id INTEGER NOT NULL,
          full_name TEXT NOT NULL,
          phone TEXT DEFAULT '',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          business_id INTEGER NOT NULL,
          telegram_id INTEGER NOT NULL,
          customer_name TEXT NOT NULL,
          phone TEXT NOT NULL,
          details TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'new',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(business_id) REFERENCES businesses(id)
        );
        ''')
        count = db.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]
        if count == 0:
            db.execute('INSERT INTO businesses(name,description) VALUES(?,?)',
                       ('کسب‌وکار نمونه', 'برای شروع، این مورد را از پنل مدیریت ویرایش کنید.'))

def list_businesses(active_only=True):
    with connect() as db:
        sql = 'SELECT * FROM businesses' + (' WHERE active=1' if active_only else '') + ' ORDER BY id'
        return db.execute(sql).fetchall()

def get_business(business_id):
    with connect() as db:
        return db.execute('SELECT * FROM businesses WHERE id=? AND active=1', (business_id,)).fetchone()

def save_customer(telegram_id, full_name, phone):
    with connect() as db:
        db.execute('''INSERT INTO customers(telegram_id,full_name,phone) VALUES(?,?,?)
        ON CONFLICT(telegram_id) DO UPDATE SET full_name=excluded.full_name, phone=excluded.phone''',
        (telegram_id, full_name, phone))

def create_order(business_id, telegram_id, customer_name, phone, details):
    with connect() as db:
        cur = db.execute('INSERT INTO orders(business_id,telegram_id,customer_name,phone,details) VALUES(?,?,?,?,?)',
                         (business_id, telegram_id, customer_name, phone, details))
        return cur.lastrowid

def recent_orders(limit=100):
    with connect() as db:
        return db.execute('''SELECT o.*, b.name AS business_name FROM orders o
          JOIN businesses b ON b.id=o.business_id ORDER BY o.id DESC LIMIT ?''', (limit,)).fetchall()

def add_business(name, description='', phone=''):
    with connect() as db:
        db.execute('INSERT INTO businesses(name,description,contact_phone) VALUES(?,?,?)',
                   (name, description, phone))
