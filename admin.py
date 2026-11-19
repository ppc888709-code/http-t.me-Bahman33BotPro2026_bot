import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from .config import ADMIN_USERNAME, ADMIN_PASSWORD
from .db import init_db, recent_orders, list_businesses, add_business

api = FastAPI(title='Business Bot Pro Control Panel', version='2.0.0')
security = HTTPBasic()

@api.on_event('startup')
def startup():
    init_db()

def verify(credentials: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(credentials.username.encode(), ADMIN_USERNAME.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    if not ADMIN_PASSWORD or not (user_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials', headers={'WWW-Authenticate':'Basic'})
    return credentials.username

class BusinessInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default='', max_length=1000)
    phone: str = Field(default='', max_length=40)

@api.get('/health')
def health():
    return {'status':'ok','service':'Business Bot Pro'}

@api.get('/')
def home(_: str = Depends(verify)):
    return {'message':'Control panel is ready','endpoints':['/businesses','/orders']}

@api.get('/businesses')
def businesses(_: str = Depends(verify)):
    return [dict(x) for x in list_businesses(active_only=False)]

@api.post('/businesses')
def create_business(payload: BusinessInput, _: str = Depends(verify)):
    try:
        add_business(payload.name, payload.description, payload.phone)
    except Exception:
        raise HTTPException(status_code=409, detail='Business name already exists')
    return {'created':True,'name':payload.name}

@api.get('/orders')
def orders(limit: int = 100, _: str = Depends(verify)):
    return [dict(x) for x in recent_orders(max(1, min(limit, 500)))]
