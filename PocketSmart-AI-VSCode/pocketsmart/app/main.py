import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .auth import COOKIE, current_user, hash_password, verify_password, issue_token, secret
from .db import connection, init_db, save_plan, get_plans, get_plan
from .models import HomeInput, PartyInput, JewelryInput, Plan
from .planner import home, party, jewelry
from .gemini import enrich

load_dotenv()
BASE = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app):
    secret()
    init_db()
    yield

app = FastAPI(title='PocketSmart AI', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE/'static'), name='static')

class Credentials(BaseModel):
    email: str
    password: str

class Registration(Credentials):
    name: str

class ProfileUpdate(BaseModel):
    name: str

def clean_name(name):
    name = name.strip()
    if not 2 <= len(name) <= 60:
        raise HTTPException(422, 'Name must contain 2 to 60 characters')
    return name

def normalized_email(value):
    email = value.strip().lower()
    if not 3 <= len(email) <= 254 or '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(422,'Enter a valid email address')
    return email

def set_cookie(response, token):
    response.set_cookie(COOKIE,token,httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','false').lower()=='true',max_age=86400)

@app.get('/')
async def index():
    return FileResponse(BASE/'static'/'index.html')

@app.get('/health')
async def health():
    return {'status':'ok'}

@app.post('/register',status_code=201)
async def register(data: Registration, response: Response):
    email = normalized_email(data.email)
    name = clean_name(data.name)
    if not 10 <= len(data.password) <= 128:
        raise HTTPException(422,'Password must contain 10 to 128 characters')
    with connection() as conn:
        if conn.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
            raise HTTPException(409,'This email is already registered')
        cursor=conn.execute('INSERT INTO users(email,password_hash,name) VALUES (?,?,?)',(email,hash_password(data.password),name))
        user_id=cursor.lastrowid
    set_cookie(response,issue_token(user_id))
    return {'id':user_id,'email':email,'name':name}

@app.post('/login')
async def login(data: Credentials, response: Response):
    email = normalized_email(data.email)
    with connection() as conn:
        row=conn.execute('SELECT id,email,name,password_hash FROM users WHERE email=?',(email,)).fetchone()
    if not row or not verify_password(data.password,row['password_hash']):
        raise HTTPException(401,'Invalid email or password')
    set_cookie(response,issue_token(row['id']))
    return {'id':row['id'],'email':row['email'],'name':row['name']}

@app.post('/token')
async def token(data: Credentials):
    email = normalized_email(data.email)
    with connection() as conn:
        row=conn.execute('SELECT id,password_hash FROM users WHERE email=?',(email,)).fetchone()
    if not row or not verify_password(data.password,row['password_hash']):
        raise HTTPException(401,'Invalid email or password')
    return {'access_token':issue_token(row['id']),'token_type':'bearer'}

@app.post('/logout')
async def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {'ok':True}

@app.get('/session-info')
async def session_info(user=Depends(current_user)):
    return user

@app.patch('/profile')
async def update_profile(data: ProfileUpdate, user=Depends(current_user)):
    name = clean_name(data.name)
    with connection() as conn:
        conn.execute('UPDATE users SET name=? WHERE id=?', (name, user['id']))
    return {**user, 'name': name}

@app.get('/session-data')
async def session_data(user=Depends(current_user)):
    plans=get_plans(user['id'])
    return {'user':user,'plan_count':len(plans),'recent':plans[:3]}

async def finish(user, plan, context, image=None, mime=None):
    plan = await enrich(plan,context,image,mime)
    plan.id=save_plan(user['id'],plan)
    return plan

@app.post('/generate-home',response_model=Plan)
async def generate_home(data: HomeInput,user=Depends(current_user)):
    return await finish(user,home(data),data.model_dump())

@app.post('/generate-party',response_model=Plan)
async def generate_party(data: PartyInput,user=Depends(current_user)):
    return await finish(user,party(data),data.model_dump())

@app.post('/generate-jewelry',response_model=Plan)
async def generate_jewelry(budget:int=Form(...),occasion:str=Form(...),style:str=Form(...),
                           outfit_color:str=Form(''),image:UploadFile|None=File(None),user=Depends(current_user)):
    data=JewelryInput(budget=budget,occasion=occasion,style=style,outfit_color=outfit_color)
    image_bytes=None
    mime=None
    if image and image.filename:
        mime=image.content_type
        if mime not in {'image/jpeg','image/png','image/webp'}:
            raise HTTPException(422,'Upload JPEG, PNG or WebP only')
        image_bytes=await image.read(3*1024*1024+1)
        if len(image_bytes)>3*1024*1024:
            raise HTTPException(413,'Image must be at most 3 MB')
        signatures={'image/jpeg':b'\xff\xd8\xff','image/png':b'\x89PNG\r\n\x1a\n','image/webp':b'RIFF'}
        if not image_bytes.startswith(signatures[mime]) or (mime=='image/webp' and image_bytes[8:12]!=b'WEBP'):
            raise HTTPException(422,'File does not match its image type')
    plan=jewelry(data)
    if image_bytes and not os.getenv('GEMINI_API_KEY'):
        plan.notes.append('The image was not analyzed because Gemini is not configured.')
    return await finish(user,plan,data.model_dump(),image_bytes,mime)

@app.get('/history')
async def history(user=Depends(current_user)):
    return get_plans(user['id'])

@app.get('/recommendations-details/{plan_id}')
async def recommendations_details(plan_id:int,user=Depends(current_user)):
    plan=get_plan(user['id'],plan_id)
    if plan is None:
        raise HTTPException(404,'Plan not found')
    return plan

if __name__=='__main__':
    import uvicorn
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000,reload=True)
