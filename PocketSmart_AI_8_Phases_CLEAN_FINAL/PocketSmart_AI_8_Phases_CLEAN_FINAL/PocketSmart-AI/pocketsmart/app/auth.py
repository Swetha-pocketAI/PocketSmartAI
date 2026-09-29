import hashlib
import hmac
import os
import secrets
import time
import jwt
from fastapi import HTTPException, Request
from .db import connection

COOKIE = 'pocketsmart_session'

def secret():
    value = os.getenv('SECRET_KEY', '')
    if len(value) < 32 or value.startswith('replace-'):
        raise RuntimeError('Set SECRET_KEY in .env to a random value of at least 32 characters')
    return value

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f'{salt.hex()}:{digest.hex()}'

def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(':')
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1)
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False

def issue_token(user_id):
    return jwt.encode({'sub':str(user_id),'exp':int(time.time())+86400}, secret(), algorithm='HS256')

def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
    if not token:
        raise HTTPException(401, 'Please sign in')
    try:
        user_id = int(jwt.decode(token, secret(), algorithms=['HS256'])['sub'])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, 'Invalid or expired session')
    with connection() as conn:
        row = conn.execute('SELECT id,email,name FROM users WHERE id=?', (user_id,)).fetchone()
    if not row:
        raise HTTPException(401, 'User no longer exists')
    return dict(row)
