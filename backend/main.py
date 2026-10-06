"""Small contact API backed by SQLite on a Railway persistent volume."""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

DB_PATH = Path(os.environ.get('DATABASE_PATH', './data/inquiries.sqlite3'))
ORIGINS = [origin.strip().rstrip('/') for origin in os.environ.get(
    'ALLOWED_ORIGINS', '').split(',') if origin.strip()]
if '*' in ORIGINS:
    raise RuntimeError('ALLOWED_ORIGINS must contain explicit origins.')


def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    return db


@asynccontextmanager
async def lifespan(app):
    if os.environ.get('RAILWAY_ENVIRONMENT_ID') and not os.environ.get('RAILWAY_VOLUME_MOUNT_PATH'):
        raise RuntimeError('Attach a persistent Railway volume before accepting inquiries.')
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS inquiries (
            id TEXT PRIMARY KEY, digest TEXT NOT NULL, payload TEXT NOT NULL,
            email TEXT NOT NULL, created_at INTEGER NOT NULL)''')
        db.execute('CREATE INDEX IF NOT EXISTS email_time ON inquiries(email, created_at)')
    yield


app = FastAPI(title='HealthUp Contact API', lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=False,
                   allow_methods=['POST', 'GET'], allow_headers=['Content-Type', 'Accept'],
                   max_age=600)


@app.middleware('http')
async def guard(request: Request, call_next):
    from starlette.responses import JSONResponse
    if request.method == 'POST':
        origin = request.headers.get('origin')
        if origin and origin not in ORIGINS:
            return JSONResponse({'detail': 'Origin not allowed.'}, status_code=403)
        if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
            return JSONResponse({'detail': 'JSON required.'}, status_code=415)
        # Read at most 16 KiB, including requests without Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 16384:
                return JSONResponse({'detail': 'Request too large.'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


class IntegrationBrief(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    brief: str = Field(min_length=10, max_length=5000)
    interest: str = Field(default='General collaboration', max_length=100)
    request_id: UUID
    website: str = Field(default='', max_length=200)

    @field_validator('name', 'brief')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Must not be blank.')
        return value


@app.get('/health')
def health():
    try:
        with connect() as db:
            db.execute('SELECT 1 FROM inquiries LIMIT 1')
    except sqlite3.Error:
        raise HTTPException(503, 'Storage unavailable.') from None
    return {'status': 'ok', 'app': 'HealthUp'}


@app.post('/api/integrate', status_code=201)
def integrate(data: IntegrationBrief):
    if data.website:
        raise HTTPException(422, 'Unable to accept this inquiry.')
    payload = data.model_dump(mode='json', exclude={'request_id', 'website'})
    payload['email'] = str(data.email).lower()
    encoded = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    now = int(time.time())
    key = str(data.request_id)
    try:
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # Contact records expire after 30 days; cleanup runs on new submissions.
            db.execute('DELETE FROM inquiries WHERE created_at < ?', (now - 30*86400,))
            previous = db.execute('SELECT digest FROM inquiries WHERE id = ?', (key,)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise HTTPException(409, 'Request identifier already used for a different inquiry.')
                return {'status': 'received', 'inquiry_id': key}
            count = db.execute('SELECT COUNT(*) FROM inquiries WHERE email = ? AND created_at > ?',
                               (payload['email'], now - 3600)).fetchone()[0]
            if count >= 5:
                raise HTTPException(429, 'Too many inquiries. Please try again in an hour.')
            db.execute('INSERT INTO inquiries VALUES (?, ?, ?, ?, ?)',
                       (key, digest, encoded, payload['email'], now))
    except sqlite3.Error:
        raise HTTPException(503, 'Your inquiry could not be saved. Please try again.') from None
    return {'status': 'received', 'inquiry_id': key}
