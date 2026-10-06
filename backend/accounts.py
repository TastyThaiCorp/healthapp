"""Account/security API. Disabled unless operational and legal deployment gates are set.
No wellness data is sent here except a separately consented encrypted backup.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from cryptography.fernet import Fernet, MultiFernet
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix='/api')
VERSION = '2026-10-06.1'
COOKIE = '__Host-healthup'
passwords = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY = passwords.hash(secrets.token_urlsafe(32))
SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email_idx TEXT UNIQUE,email_enc TEXT,name_enc TEXT,password TEXT,verified INTEGER DEFAULT 0,role TEXT DEFAULT 'member',plan TEXT DEFAULT 'free',country TEXT,created INTEGER,mfa_enc TEXT,last_totp INTEGER DEFAULT -1,cloud_consent INTEGER DEFAULT 0,customer TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT,csrf_enc TEXT,expires INTEGER,created INTEGER,mfa INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY,user_id TEXT,kind TEXT,expires INTEGER,used INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,user_id TEXT,body_enc TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS backups(user_id TEXT PRIMARY KEY,body_enc TEXT,updated INTEGER);
CREATE TABLE IF NOT EXISTS audits(id TEXT PRIMARY KEY,actor TEXT,action TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,user_id TEXT,kind TEXT,body_enc TEXT,status TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS limits(key TEXT PRIMARY KEY,start INTEGER,hits INTEGER);
CREATE TABLE IF NOT EXISTS webhooks(id TEXT PRIMARY KEY,created INTEGER);
'''


def settings():
    return {key: os.getenv(key, '') for key in ['AUTH_ENABLED','HEALTHUP_LEGAL_REVIEWED','ACCOUNT_DB_PATH',
        'ACCOUNT_ENCRYPTION_KEYS','ACCOUNT_HASH_KEY','HEALTHUP_COMPANY_NAME','HEALTHUP_PRIVACY_EMAIL',
        'APP_URL','SMTP_HOST','SMTP_USER','SMTP_PASSWORD','SMTP_FROM']}


def enabled():
    s = settings()
    if os.getenv('RAILWAY_ENVIRONMENT_ID') and os.getenv('HEALTHUP_ENV')=='test':return False
    return (s['AUTH_ENABLED']=='true' and s['HEALTHUP_LEGAL_REVIEWED']=='true' and
        all(s[k] for k in s if k not in ['AUTH_ENABLED','HEALTHUP_LEGAL_REVIEWED']) and
        (s['APP_URL'].startswith('https://') or os.getenv('HEALTHUP_ENV')=='test'))


def require_enabled():
    if not enabled():
        raise HTTPException(503, 'Accounts are not activated. Local wellness tools remain available.')


def cipher():
    try:
        return MultiFernet([Fernet(k.strip().encode()) for k in os.environ['ACCOUNT_ENCRYPTION_KEYS'].split(',')])
    except (KeyError, ValueError):
        raise HTTPException(503, 'Account encryption is not configured.') from None


def encrypt(value):
    return cipher().encrypt(json.dumps(value).encode()).decode()


def decrypt(value):
    return json.loads(cipher().decrypt(value.encode()))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(value):
    key = os.getenv('ACCOUNT_HASH_KEY','').encode()
    if len(key)<32:
        raise HTTPException(503, 'Account security configuration is incomplete.')
    return hmac.new(key,value.strip().lower().encode(),hashlib.sha256).hexdigest()


def database():
    path=Path(os.environ['ACCOUNT_DB_PATH'])
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    connection=sqlite3.connect(path,timeout=10)
    os.chmod(path,0o600)
    connection.row_factory=sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.executescript(SCHEMA)
    return connection


def audit(db,actor,action):
    db.execute('INSERT INTO audits VALUES(?,?,?,?)',(secrets.token_hex(16),actor,action,int(time.time())))


def receipt(db,user_id,body):
    db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(secrets.token_hex(16),user_id,encrypt(body),int(time.time())))


def check_origin(request):
    allowed={urlsplit(os.environ['APP_URL']).scheme+'://'+urlsplit(os.environ['APP_URL']).netloc}
    origin=request.headers.get('origin','')
    if origin not in allowed:
        raise HTTPException(403,'Open HealthUp from its approved app address.')


def rate(request,action,limit=20):
    key=identity((request.client.host if request.client else 'unknown')+':'+action)
    now=int(time.time())
    with database() as db:
        db.execute('DELETE FROM limits WHERE start<?',(now-3600,))
        row=db.execute('SELECT * FROM limits WHERE key=?',(key,)).fetchone()
        if row and now-row['start']<60 and row['hits']>=limit:
            raise HTTPException(429,'Please wait a minute before trying again.',headers={'Retry-After':'60'})
        if not row or now-row['start']>=60:
            db.execute('INSERT OR REPLACE INTO limits VALUES(?,?,?)',(key,now,1))
        else:
            db.execute('UPDATE limits SET hits=hits+1 WHERE key=?',(key,))


def credential_ok(encoded,password):
    try:return passwords.verify(encoded,password)
    except (VerificationError,InvalidHashError):return False


def password_policy(password):
    if len(password)<12 or len(password)>128 or password.lower() in {'password1234','healthup12345','123456789012'}:
        raise HTTPException(422,'Use a unique password of 12–128 characters. A long passphrase works well.')


def notice_current(user_id):
    with database() as db:rows=db.execute('SELECT body_enc FROM receipts WHERE user_id=? ORDER BY rowid DESC',(user_id,)).fetchall()
    for row in rows:
        record=decrypt(row['body_enc'])
        if record.get('essential_consent'):
            return record.get('notice_version')==VERSION
    return False


def safe_user(user):
    return {'id':user['id'],'email':decrypt(user['email_enc']),'name':decrypt(user['name_enc']),
        'role':user['role'],'plan':user['plan'],'verified':bool(user['verified']),
        'cloud_consent':bool(user['cloud_consent']),'notice_ack_required':not notice_current(user['id'])}


def current(request,write=False,staff=False):
    require_enabled()
    token=request.cookies.get(COOKIE if os.getenv('HEALTHUP_ENV')!='test' else 'healthup-test','')
    with database() as db:
        row=db.execute('SELECT * FROM sessions WHERE token=? AND expires>?',(digest(token),int(time.time()))).fetchone()
        if not row:raise HTTPException(401,'Please sign in again.')
        user=db.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()
        if not user:raise HTTPException(401,'Please sign in again.')
        if write:
            check_origin(request)
            if not hmac.compare_digest(request.headers.get('x-csrf-token',''),decrypt(row['csrf_enc'])):
                raise HTTPException(403,'Refresh HealthUp before making this change.')
        if staff and (user['role']!='staff' or not row['mfa'] or row['created']<time.time()-1800):
            raise HTTPException(403,'Verified staff multi-factor access is required.')
        return user,row


def mail(address,kind,token):
    # Never log tokens or recipients. No health entries are included in messages.
    message=EmailMessage()
    message['From']=os.environ['SMTP_FROM']
    message['To']=address
    message['Subject']='HealthUp · '+('Verify your email' if kind=='verify' else 'Reset your password')
    link=os.environ['APP_URL'].rstrip('/')+'/#account?'+kind+'='+token
    message.set_content('Open this link to '+('verify your HealthUp email' if kind=='verify' else 'reset your HealthUp password')+':\n\n'+link+'\n\nIf you did not request this, ignore it. This link expires shortly. HealthUp is not a crisis service.')
    try:
        with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=10) as server:
            server.starttls()
            server.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
            server.send_message(message)
    except (OSError,smtplib.SMTPException):
        raise HTTPException(503,'Email delivery is unavailable. Please try again later.') from None


class Registration(BaseModel):
    email:EmailStr
    password:str=Field(min_length=12,max_length=128)
    name:str=Field(default='',max_length=60)
    country:str=Field(default='US',min_length=2,max_length=2)
    adult:bool
    terms:bool
    essential_consent:bool
    wellness_ack:bool
    signed_name:str=Field(min_length=1,max_length=100)
    notice_version:str


class Login(BaseModel):
    email:EmailStr
    password:str=Field(max_length=128)
    otp:str=Field(default='',max_length=6)


class EmailInput(BaseModel):
    email:EmailStr


class TokenInput(BaseModel):
    token:str=Field(min_length=20,max_length=200)
    password:str=Field(default='',max_length=128)


class ConfirmPassword(BaseModel):
    password:str=Field(max_length=128)


class CloudConsent(BaseModel):
    enabled:bool
    notice_version:str


class PrivacyRequest(BaseModel):
    kind:str=Field(pattern='^(access|correction|deletion|appeal|other)$')
    message:str=Field(default='',max_length=1500)


@router.get('/auth/config')
def config():
    ready=enabled()
    return {'enabled':ready,'notice_version':VERSION,'company':os.getenv('HEALTHUP_COMPANY_NAME') or None,
        'privacy_email':os.getenv('HEALTHUP_PRIVACY_EMAIL') or None,
        'regions':os.getenv('HEALTHUP_ALLOWED_COUNTRIES','US').split(','),'minimum_age':18,
        'app_url':os.getenv('APP_URL') or None,'billing_enabled':ready and billing_enabled(),'selling_data':False,'targeted_advertising':False}


@router.post('/auth/register')
def register(data:Registration,request:Request):
    require_enabled();check_origin(request);rate(request,'register',5);password_policy(data.password)
    if not data.signed_name.strip() or not all([data.adult,data.terms,data.essential_consent,data.wellness_ack]) or data.notice_version!=VERSION:
        raise HTTPException(422,'Adult eligibility and the current required acknowledgements must be accepted.')
    if data.country not in os.getenv('HEALTHUP_ALLOWED_COUNTRIES','US').split(','):
        raise HTTPException(422,'Accounts are not available in your region yet. Local tools remain available.')
    address=str(data.email).lower();email_idx=identity(address)
    message={'message':'If this address is eligible, a verification email has been sent. Check your inbox.'}
    with database() as db:
        if db.execute('SELECT id FROM users WHERE email_idx=?',(email_idx,)).fetchone():
            passwords.hash(data.password)
            return message
        user_id=secrets.token_hex(16);token=secrets.token_urlsafe(32);now=int(time.time())
        db.execute('INSERT INTO users(id,email_idx,email_enc,name_enc,password,country,created) VALUES(?,?,?,?,?,?,?)',
            (user_id,email_idx,encrypt(address),encrypt(data.name),passwords.hash(data.password),data.country,now))
        db.execute('INSERT INTO tokens VALUES(?,?,?,?,0)',(digest(token),user_id,'verify',now+86400))
        receipt(db,user_id,{'notice_version':VERSION,'essential_consent':True,'terms':True,'wellness_ack':True,
            'adult':True,'signed_name':data.signed_name,'cloud_backup':False,'sale_or_ads':False,'timestamp':now})
        mail(address,'verify',token)
        audit(db,user_id,'registration')
    return message


@router.post('/auth/verify')
def verify(data:TokenInput,request:Request):
    require_enabled();check_origin(request);rate(request,'verify',10)
    with database() as db:
        token=db.execute('SELECT * FROM tokens WHERE token=? AND kind=? AND used=0 AND expires>?',
            (digest(data.token),'verify',int(time.time()))).fetchone()
        if not token:raise HTTPException(400,'This verification link is invalid or expired.')
        db.execute('UPDATE tokens SET used=1 WHERE token=?',(token['token'],))
        db.execute('UPDATE users SET verified=1 WHERE id=?',(token['user_id'],))
        audit(db,token['user_id'],'email_verified')
    return {'message':'Email verified. You can now sign in.'}


@router.post('/auth/login')
def login(data:Login,request:Request,response:Response):
    require_enabled();check_origin(request);rate(request,'login',10)
    with database() as db:
        user=db.execute('SELECT * FROM users WHERE email_idx=?',(identity(str(data.email)),)).fetchone()
        valid=credential_ok(user['password'] if user else DUMMY,data.password)
        if not user or not valid or not user['verified']:
            raise HTTPException(401,'The email/password combination is unavailable. Verify your email if you just registered.')
        mfa=False
        if user['role']=='staff':
            if not user['mfa_enc']:raise HTTPException(403,'Staff multi-factor enrollment is required.')
            totp=pyotp.TOTP(decrypt(user['mfa_enc']))
            counter=int(time.time())//30
            matched=next((n for n in [counter-1,counter,counter+1] if hmac.compare_digest(totp.at(n*30),data.otp)),None)
            if matched is None or matched<=user['last_totp']:
                raise HTTPException(401,'Enter a current, unused authenticator code.')
            db.execute('UPDATE users SET last_totp=? WHERE id=?',(matched,user['id']))
            mfa=True
        if passwords.check_needs_rehash(user['password']):
            db.execute('UPDATE users SET password=? WHERE id=?',(passwords.hash(data.password),user['id']))
        token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32);now=int(time.time())
        db.execute('DELETE FROM sessions WHERE expires<?',(now,))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',(digest(token),user['id'],encrypt(csrf),now+604800,now,int(mfa)))
        audit(db,user['id'],'login')
    test=os.getenv('HEALTHUP_ENV')=='test'
    response.set_cookie('healthup-test' if test else COOKIE,token,max_age=604800,httponly=True,secure=not test,samesite='strict',path='/')
    return {'user':safe_user(user),'csrf':csrf,'checkin_required':True}


@router.get('/auth/me')
def me(request:Request):
    user,session=current(request)
    return {'user':safe_user(user),'csrf':decrypt(session['csrf_enc'])}


@router.post('/auth/logout')
def logout(request:Request,response:Response):
    user,session=current(request,write=True)
    with database() as db:db.execute('DELETE FROM sessions WHERE token=?',(session['token'],))
    response.delete_cookie('healthup-test' if os.getenv('HEALTHUP_ENV')=='test' else COOKIE,path='/',secure=os.getenv('HEALTHUP_ENV')!='test',httponly=True,samesite='strict')
    return {'message':'Signed out.'}


@router.post('/auth/revoke-sessions')
def revoke(request:Request):
    user,_=current(request,write=True)
    with database() as db:
        db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],));audit(db,user['id'],'sessions_revoked')
    return {'message':'All sessions have been revoked. Sign in again.'}


@router.post('/auth/forgot-password')
def forgot(data:EmailInput,request:Request):
    require_enabled();check_origin(request);rate(request,'reset',3)
    with database() as db:
        user=db.execute('SELECT * FROM users WHERE email_idx=? AND verified=1',(identity(str(data.email)),)).fetchone()
        if user:
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM tokens WHERE user_id=? AND kind=?',(user['id'],'reset'))
            db.execute('INSERT INTO tokens VALUES(?,?,?,?,0)',(digest(token),user['id'],'reset',int(time.time())+1800))
            mail(decrypt(user['email_enc']),'reset',token)
    return {'message':'If an eligible account exists, a reset link has been sent.'}


@router.post('/auth/reset-password')
def reset(data:TokenInput,request:Request):
    require_enabled();check_origin(request);rate(request,'reset-use',5);password_policy(data.password)
    hashed=passwords.hash(data.password)
    with database() as db:
        token=db.execute('SELECT * FROM tokens WHERE token=? AND kind=? AND used=0 AND expires>?',
            (digest(data.token),'reset',int(time.time()))).fetchone()
        if not token:raise HTTPException(400,'This reset link is invalid or expired.')
        db.execute('UPDATE tokens SET used=1 WHERE token=?',(token['token'],))
        db.execute('UPDATE users SET password=? WHERE id=?',(hashed,token['user_id']))
        db.execute('DELETE FROM sessions WHERE user_id=?',(token['user_id'],));audit(db,token['user_id'],'password_reset')
    return {'message':'Password changed. Sign in with your new password.'}


@router.get('/account/consents')
def consents(request:Request):
    user,_=current(request)
    with database() as db:
        records=db.execute('SELECT body_enc,created FROM receipts WHERE user_id=? ORDER BY created DESC',(user['id'],)).fetchall()
    return {'receipts':[{'created':r['created'],'acknowledgement':decrypt(r['body_enc'])} for r in records]}


@router.post('/account/cloud-consent')
def cloud_consent(data:CloudConsent,request:Request):
    user,_=current(request,write=True)
    if data.notice_version!=VERSION:raise HTTPException(422,'Read and acknowledge the current cloud backup notice.')
    with database() as db:
        db.execute('UPDATE users SET cloud_consent=? WHERE id=?',(int(data.enabled),user['id']))
        if not data.enabled:db.execute('DELETE FROM backups WHERE user_id=?',(user['id'],))
        receipt(db,user['id'],{'notice_version':VERSION,'cloud_backup':data.enabled,'timestamp':int(time.time())})
        audit(db,user['id'],'cloud_consent_changed')
    return {'cloud_consent':data.enabled}


@router.get('/account/export')
def account_export(request:Request):
    user,_=current(request)
    with database() as db:
        backup=db.execute('SELECT body_enc FROM backups WHERE user_id=?',(user['id'],)).fetchone()
        records=db.execute('SELECT body_enc FROM receipts WHERE user_id=?',(user['id'],)).fetchall()
    return {'product':'HealthUp','account':safe_user(user),'consents':[decrypt(r['body_enc']) for r in records],
        'backup':decrypt(backup['body_enc']) if backup else None}


@router.post('/account/backup')
async def backup(request:Request):
    user,_=current(request,write=True)
    if not notice_current(user['id']):raise HTTPException(403,'Review the current required acknowledgements before uploading.')
    if not user['cloud_consent']:raise HTTPException(403,'Cloud backup consent is required.')
    if user['plan']!='plus':raise HTTPException(403,'An active HealthUp Plus subscription is required.')
    data=await request.json()
    if data.get('product')!='HealthUp' or data.get('version')!=1 or not isinstance(data.get('state'),dict):
        raise HTTPException(422,'Choose a HealthUp export.')
    if len(json.dumps(data))>2000000:raise HTTPException(413,'The backup is too large.')
    with database() as db:
        db.execute('INSERT OR REPLACE INTO backups VALUES(?,?,?)',(user['id'],encrypt(data),int(time.time())))
        audit(db,user['id'],'backup_uploaded')
    return {'message':'Encrypted cloud backup saved.'}


@router.get('/account/backup')
def restore(request:Request):
    user,_=current(request)
    if not user['cloud_consent']:raise HTTPException(403,'Cloud backup consent is not enabled.')
    if user['plan']!='plus':raise HTTPException(403,'An active HealthUp Plus subscription is required.')
    with database() as db:row=db.execute('SELECT * FROM backups WHERE user_id=?',(user['id'],)).fetchone()
    if not row:raise HTTPException(404,'No cloud backup has been saved yet.')
    return decrypt(row['body_enc'])


@router.delete('/account/backup')
def delete_backup(request:Request):
    user,_=current(request,write=True)
    with database() as db:db.execute('DELETE FROM backups WHERE user_id=?',(user['id'],))
    return {'message':'Cloud backup deleted.'}


@router.post('/account/privacy-request')
def privacy_request(data:PrivacyRequest,request:Request):
    user,_=current(request,write=True);rate(request,'privacy-request',5)
    request_id=secrets.token_hex(16)
    with database() as db:
        db.execute('INSERT INTO requests VALUES(?,?,?,?,?,?)',(request_id,user['id'],data.kind,encrypt(data.message),'open',int(time.time())))
    return {'id':request_id,'message':'Request recorded. Your request ID is '+request_id+'. Keep it for your records.'}


@router.get('/account/privacy-requests')
def privacy_requests(request:Request):
    user,_=current(request)
    with database() as db:rows=db.execute('SELECT id,kind,status,created FROM requests WHERE user_id=? ORDER BY created DESC',(user['id'],)).fetchall()
    return {'requests':[dict(r) for r in rows]}


@router.delete('/account')
def delete_account(data:ConfirmPassword,request:Request,response:Response):
    user,_=current(request,write=True);rate(request,'delete-account',5)
    if not credential_ok(user['password'],data.password):raise HTTPException(401,'Confirm your password to delete the account.')
    if user['plan']=='plus':raise HTTPException(409,'Cancel the active subscription in the billing portal before deleting your account.')
    with database() as db:
        for table in ['sessions','tokens','receipts','backups','requests']:
            db.execute(f'DELETE FROM {table} WHERE user_id=?',(user['id'],))
        db.execute('DELETE FROM users WHERE id=?',(user['id'],));audit(db,user['id'],'account_deleted')
    response.delete_cookie('healthup-test' if os.getenv('HEALTHUP_ENV')=='test' else COOKIE,path='/')
    return {'message':'Account and stored backup deleted. Local device data can be deleted separately in Settings.'}


@router.get('/admin/overview')
def admin(request:Request):
    user,_=current(request,staff=True)
    with database() as db:
        totals={key:db.execute(query).fetchone()[0] for key,query in {
            'accounts':'SELECT COUNT(*) FROM users','verified':'SELECT COUNT(*) FROM users WHERE verified=1',
            'plus':'SELECT COUNT(*) FROM users WHERE plan="plus"','open_requests':'SELECT COUNT(*) FROM requests WHERE status="open"'}.items()}
        requests=db.execute('SELECT id,kind,status,created FROM requests ORDER BY created DESC LIMIT 50').fetchall()
        audits=db.execute('SELECT action,created FROM audits ORDER BY created DESC LIMIT 25').fetchall()
        audit(db,user['id'],'staff_overview')
    return {'totals':totals,'requests':[dict(r) for r in requests],'audits':[dict(r) for r in audits],
        'private_entries_accessible':False,'legal_notice_version':VERSION}


class RequestStatus(BaseModel):
    status:str=Field(pattern='^(open|in_review|completed|denied)$')


@router.post('/admin/requests/{request_id}')
def request_status(request_id:str,data:RequestStatus,request:Request):
    user,_=current(request,write=True,staff=True)
    with database() as db:
        if not db.execute('SELECT id FROM requests WHERE id=?',(request_id,)).fetchone():raise HTTPException(404,'Request not found.')
        db.execute('UPDATE requests SET status=? WHERE id=?',(data.status,request_id));audit(db,user['id'],'privacy_request_'+data.status)
    return {'message':'Request status updated. Complete the underlying privacy action before marking a request completed.'}


def billing_enabled():
    return all(os.getenv(k) for k in ['STRIPE_SECRET_KEY','STRIPE_PRICE_ID','STRIPE_WEBHOOK_SECRET']) and os.getenv('BILLING_TERMS_REVIEWED')=='true'


async def stripe_call(method,path,data=None):
    if not billing_enabled():raise HTTPException(503,'Billing is not connected. The core app remains free.')
    async with httpx.AsyncClient(timeout=12) as client:
        try:
            response=await client.request(method,'https://api.stripe.com/v1/'+path,auth=(os.environ['STRIPE_SECRET_KEY'],''),data=data)
            response.raise_for_status();return response.json()
        except (httpx.HTTPError,ValueError):raise HTTPException(503,'Billing provider is unavailable. You have not been charged by this action.') from None


@router.get('/billing/plans')
async def plans():
    if not enabled() or not billing_enabled():return {'available':False,'free':True,'plus_features':['Encrypted cloud backup','Restore on another device'],'message':'Plus is not on sale until account and billing connections are configured.'}
    price=await stripe_call('GET','prices/'+os.environ['STRIPE_PRICE_ID'])
    if not price.get('active') or not price.get('recurring') or price['recurring'].get('interval')!='month' or price['recurring'].get('interval_count')!=1:
        raise HTTPException(503,'A current monthly subscription price must be configured.')
    return {'available':True,'amount':price['unit_amount'],'currency':price['currency'],'interval':'month','plus_features':['Encrypted cloud backup','Restore on another device']}


class Purchase(BaseModel):
    renewal_acknowledged:bool
    notice_version:str


@router.post('/billing/checkout')
async def checkout(data:Purchase,request:Request):
    user,_=current(request,write=True)
    if not notice_current(user['id']):raise HTTPException(403,'Review the current required acknowledgements before purchasing.')
    if not data.renewal_acknowledged or data.notice_version!=VERSION:raise HTTPException(422,'Acknowledge the current subscription terms before purchase.')
    if user['plan']=='plus':raise HTTPException(409,'You already have Plus. Use Manage subscription.')
    price=await plans()
    payload={'mode':'subscription','line_items[0][price]':os.environ['STRIPE_PRICE_ID'],'line_items[0][quantity]':'1',
        'client_reference_id':user['id'],'subscription_data[metadata][healthup_user]':user['id'],
        'success_url':os.environ['APP_URL'].rstrip('/')+'/?billing=success#account',
        'cancel_url':os.environ['APP_URL'].rstrip('/')+'/?billing=cancelled#account'}
    if user['customer']:payload['customer']=user['customer']
    else:payload['customer_email']=decrypt(user['email_enc'])
    session=await stripe_call('POST','checkout/sessions',payload)
    with database() as db:receipt(db,user['id'],{'notice_version':VERSION,'renewal_acknowledged':True,'timestamp':int(time.time()),'checkout_id':session['id'],'amount':price['amount'],'currency':price['currency'],'interval':price['interval']})
    return {'url':session['url']}


@router.post('/billing/portal')
async def portal(request:Request):
    user,_=current(request,write=True)
    if not user['customer']:raise HTTPException(404,'No billing customer is connected yet.')
    session=await stripe_call('POST','billing_portal/sessions',{'customer':user['customer'],'return_url':os.environ['APP_URL'].rstrip('/')+'/#account'})
    return {'url':session['url']}


@router.post('/billing/webhook')
async def webhook(request:Request):
    if not billing_enabled():raise HTTPException(503,'Billing is not configured.')
    body=await request.body();signature=request.headers.get('stripe-signature','')
    try:
        parts=signature.split(',');timestamp=int(next(p[2:] for p in parts if p.startswith('t=')))
        values=[p[3:] for p in parts if p.startswith('v1=')]
    except (StopIteration,ValueError):raise HTTPException(400,'Invalid signature.') from None
    expected=hmac.new(os.environ['STRIPE_WEBHOOK_SECRET'].encode(),str(timestamp).encode()+b'.'+body,hashlib.sha256).hexdigest()
    if abs(time.time()-timestamp)>300 or not any(hmac.compare_digest(expected,value) for value in values):raise HTTPException(400,'Invalid signature.')
    try:event=json.loads(body)
    except ValueError:raise HTTPException(400,'Invalid event.') from None
    kind=event.get('type');obj=event.get('data',{}).get('object',{})
    subscription=None
    if kind in ['customer.subscription.created','customer.subscription.updated','customer.subscription.deleted']:
        subscription=await stripe_call('GET','subscriptions/'+obj['id'])
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT id FROM webhooks WHERE id=?',(event.get('id'),)).fetchone():return {'received':True}
        if kind=='checkout.session.completed' and obj.get('mode')=='subscription':
            user_id=obj.get('client_reference_id')
            if user_id and obj.get('customer'):db.execute('UPDATE users SET customer=? WHERE id=?',(obj['customer'],user_id))
            # The subscription webhook, not a client redirect, grants the entitlement.
        if kind in ['customer.subscription.created','customer.subscription.updated','customer.subscription.deleted']:
            # Retrieve canonical status to handle out-of-order delivery.
            user_id=subscription.get('metadata',{}).get('healthup_user')
            known_price=any(item.get('price',{}).get('id')==os.environ['STRIPE_PRICE_ID'] for item in subscription.get('items',{}).get('data',[]))
            active=subscription.get('status') in ['active','trialing'] and known_price
            if user_id:
                db.execute('UPDATE users SET plan=?,customer=? WHERE id=?',('plus' if active else 'free',subscription.get('customer'),user_id))
                audit(db,user_id,'subscription_updated')
        db.execute('INSERT INTO webhooks VALUES(?,?)',(event['id'],int(time.time())))
    return {'received':True}


class Acknowledgement(BaseModel):
    adult:bool
    terms:bool
    essential_consent:bool
    wellness_ack:bool
    signed_name:str=Field(min_length=1,max_length=100)
    notice_version:str


@router.post('/account/acknowledge')
def acknowledge(data:Acknowledgement,request:Request):
    user,_=current(request,write=True)
    if not all([data.adult,data.terms,data.essential_consent,data.wellness_ack]) or not data.signed_name.strip() or data.notice_version!=VERSION:
        raise HTTPException(422,'Review and accept the current required notices to continue with account services.')
    with database() as db:
        receipt(db,user['id'],{'notice_version':VERSION,'essential_consent':True,'terms':True,'wellness_ack':True,'adult':True,'signed_name':data.signed_name,'timestamp':int(time.time())})
        audit(db,user['id'],'notice_acknowledged')
    return {'message':'Current acknowledgement recorded. Optional sharing remains unchanged.'}
