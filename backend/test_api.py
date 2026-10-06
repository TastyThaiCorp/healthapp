import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient

os.environ['DATABASE_PATH'] = str(Path(tempfile.mkdtemp()) / 'inquiries.sqlite3')
os.environ['ALLOWED_ORIGINS'] = 'https://tastythaicorp.github.io'
from main import app, DB_PATH

with TestClient(app) as client:
    origin={'Origin':'https://tastythaicorp.github.io'}
    payload={'name':'Alex','email':'alex@example.com','brief':'A meaningful developer collaboration.','request_id':str(uuid4())}
    assert client.get('/health').status_code==200
    r=client.post('/api/integrate',json=payload,headers=origin)
    assert r.status_code==201,r.text
    assert r.json()['inquiry_id']==payload['request_id']
    assert client.post('/api/integrate',json=payload,headers=origin).status_code==201
    with sqlite3.connect(DB_PATH) as db:
        assert db.execute('SELECT COUNT(*) FROM inquiries').fetchone()[0]==1
    assert client.post('/api/integrate',json={**payload,'brief':'Changed content for the same request.'},headers=origin).status_code==409
    assert client.post('/api/integrate',json={**payload,'email':'invalid','request_id':str(uuid4())},headers=origin).status_code==422
    assert client.post('/api/integrate',json=payload,headers={'Origin':'https://untrusted.example'}).status_code==403
    preflight=client.options('/api/integrate',headers={**origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
    assert preflight.status_code==200
    assert preflight.headers['access-control-allow-origin']==origin['Origin']
    assert client.post('/api/integrate',content='x'*17000,headers={'Content-Type':'application/json'}).status_code==413
    assert client.post('/api/integrate',json={**payload,'website':'spam','request_id':str(uuid4())}).status_code==422
    for _ in range(4):
        assert client.post('/api/integrate',json={**payload,'request_id':str(uuid4())}).status_code==201
    assert client.post('/api/integrate',json={**payload,'request_id':str(uuid4())}).status_code==429
    assert client.get('/index.html').status_code==404
print('PASS: persistent save, idempotent retries, validation, origin enforcement, CORS, body limit, honeypot, rate limit, API-only hosting')
