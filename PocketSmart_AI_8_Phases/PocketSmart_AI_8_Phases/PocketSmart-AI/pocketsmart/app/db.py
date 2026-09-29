import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def db_path():
    return os.getenv('DATABASE_PATH', './pocketsmart.sqlite3')

@contextmanager
def connection():
    path = db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
          name TEXT NOT NULL DEFAULT '');
          CREATE TABLE IF NOT EXISTS plans (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
          kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
          CREATE INDEX IF NOT EXISTS idx_plans_user ON plans(user_id, id DESC);''')
        columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)')}
        if 'name' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''")

def save_plan(user_id, plan):
    with connection() as conn:
        cursor = conn.execute('INSERT INTO plans (user_id,kind,payload) VALUES (?,?,?)',
                              (user_id, plan.kind, plan.model_dump_json()))
        return cursor.lastrowid

def get_plans(user_id):
    with connection() as conn:
        rows = conn.execute('SELECT id,kind,payload,created_at FROM plans WHERE user_id=? ORDER BY id DESC LIMIT 50', (user_id,)).fetchall()
    return [{'id':r['id'], 'kind':r['kind'], 'created_at':r['created_at'], 'plan':json.loads(r['payload'])} for r in rows]

def get_plan(user_id, plan_id):
    with connection() as conn:
        row = conn.execute('SELECT payload FROM plans WHERE user_id=? AND id=?', (user_id,plan_id)).fetchone()
    return json.loads(row['payload']) if row else None
