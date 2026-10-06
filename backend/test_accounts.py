"""Security integration tests use an ephemeral DB and a mocked mail/Stripe boundary."""
import hashlib,hmac,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
from cryptography.fernet import Fernet
import pyotp
from fastapi.testclient import TestClient
import main,accounts

with tempfile.TemporaryDirectory() as folder:
 env={'AUTH_ENABLED':'true','HEALTHUP_LEGAL_REVIEWED':'true','ACCOUNT_DB_PATH':folder+'/accounts.sqlite3',
 'ACCOUNT_ENCRYPTION_KEYS':Fernet.generate_key().decode(),'ACCOUNT_HASH_KEY':'test-only-hmac-key-'+('x'*32),
 'HEALTHUP_COMPANY_NAME':'Test operator','HEALTHUP_PRIVACY_EMAIL':'privacy@example.com',
 'APP_URL':'http://testserver','SMTP_HOST':'fixture','SMTP_USER':'fixture','SMTP_PASSWORD':'fixture','SMTP_FROM':'test@example.com',
 'HEALTHUP_ENV':'test','STRIPE_SECRET_KEY':'test-fixture','STRIPE_PRICE_ID':'price_fixture','STRIPE_WEBHOOK_SECRET':'fixture-secret','BILLING_TERMS_REVIEWED':'true'}
 messages=[]
 def mail(address,kind,token):messages.append((address,kind,token))
 with patch.dict(os.environ,env),patch.object(accounts,'mail',mail),TestClient(main.app) as client:
  origin={'Origin':'http://testserver'}
  assert client.get('/api/auth/config').json()['enabled']
  assert client.get('/api/admin/overview').status_code==401
  registration={'email':'person@example.com','password':'a unique long test passphrase','name':'Test person','country':'US',
   'adult':True,'terms':True,'essential_consent':True,'wellness_ack':True,'signed_name':'Test person','notice_version':accounts.VERSION}
  for key in ['adult','terms','essential_consent','wellness_ack']:
   assert client.post('/api/auth/register',json={**registration,key:False},headers=origin).status_code==422
  with accounts.database() as db:db.execute('DELETE FROM limits')
  assert client.post('/api/auth/register',json=registration,headers={'Origin':'https://evil.example'}).status_code==403
  assert client.post('/api/auth/register',json=registration,headers=origin).status_code==200
  assert len(messages)==1 and messages[0][1]=='verify'
  token=messages[0][2]
  assert client.post('/api/auth/login',json={'email':registration['email'],'password':registration['password']},headers=origin).status_code==401
  assert client.post('/api/auth/verify',json={'token':token},headers=origin).status_code==200
  assert client.post('/api/auth/verify',json={'token':token},headers=origin).status_code==400
  login=client.post('/api/auth/login',json={'email':registration['email'],'password':registration['password']},headers=origin)
  assert login.status_code==200
  assert login.json()['checkin_required']
  assert 'HttpOnly' in login.headers['set-cookie'] and 'SameSite=strict' in login.headers['set-cookie']
  user_id=login.json()['user']['id'];csrf=login.json()['csrf'];headers={**origin,'X-CSRF-Token':csrf}
  assert client.get('/api/auth/me').json()['user']['id']==user_id
  with patch.object(accounts,'VERSION','test-new-notice'):
   assert client.get('/api/auth/me').json()['user']['notice_ack_required']
   acknowledgement={key:registration[key] for key in ['adult','terms','essential_consent','wellness_ack','signed_name','notice_version']}
   assert client.post('/api/account/acknowledge',json=acknowledgement,headers=headers).status_code==422
   acknowledgement['notice_version']='test-new-notice'
   assert client.post('/api/account/acknowledge',json=acknowledgement,headers=headers).status_code==200
   assert not client.get('/api/auth/me').json()['user']['notice_ack_required']
   assert not client.get('/api/auth/me').json()['user']['cloud_consent']
  acknowledgement['notice_version']=accounts.VERSION
  assert client.post('/api/account/acknowledge',json=acknowledgement,headers=headers).status_code==200
  assert client.post('/api/account/cloud-consent',json={'enabled':True,'notice_version':accounts.VERSION},headers=origin).status_code==403
  assert client.get('/api/admin/overview').status_code==403
  assert client.post('/api/account/backup',json={'product':'HealthUp','version':1,'state':{}},headers=headers).status_code==403
  assert client.post('/api/account/cloud-consent',json={'enabled':True,'notice_version':accounts.VERSION},headers=headers).status_code==200
  assert client.post('/api/account/backup',json={'product':'HealthUp','version':1,'state':{}},headers=headers).status_code==403
  with accounts.database() as db:
   row=db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
   assert registration['email'] not in row['email_enc'] and registration['name'] not in row['name_enc']
   assert row['password'].startswith('$argon2id$') and registration['password'] not in row['password']
  async def stripe_fixture(method,path,data=None):
   if path.startswith('subscriptions/'):
    return {'status':'active','customer':'cus_fixture','metadata':{'healthup_user':user_id},'items':{'data':[{'price':{'id':'price_fixture'}}]}}
   return {'active':True,'recurring':{'interval':'month','interval_count':1},'unit_amount':599,'currency':'usd'}
  def signed(event,stamp=None):
   stamp=stamp or int(time.time());body=json.dumps(event).encode()
   sig=hmac.new(env['STRIPE_WEBHOOK_SECRET'].encode(),str(stamp).encode()+b'.'+body,hashlib.sha256).hexdigest()
   return body,{'Stripe-Signature':f't={stamp},v1={sig}','Content-Type':'application/json'}
  event={'id':'evt_fixture','type':'customer.subscription.updated','data':{'object':{'id':'sub_fixture'}}}
  body,signature=signed(event)
  assert client.post('/api/billing/webhook',content=body,headers={'Stripe-Signature':'t=1,v1=forged','Content-Type':'application/json'}).status_code==400
  stale,stale_signature=signed(event,int(time.time())-1000)
  assert client.post('/api/billing/webhook',content=stale,headers=stale_signature).status_code==400
  with patch.object(accounts,'stripe_call',stripe_fixture):
   assert client.post('/api/billing/webhook',content=body,headers=signature).status_code==200
   assert client.post('/api/billing/webhook',content=body,headers=signature).status_code==200
  assert client.get('/api/auth/me').json()['user']['plan']=='plus'
  backup={'product':'HealthUp','version':1,'state':{'private':'A private journal test phrase'}}
  assert client.post('/api/account/backup',json=backup,headers=headers).status_code==200
  with accounts.database() as db:assert 'private journal' not in db.execute('SELECT body_enc FROM backups').fetchone()[0]
  assert client.get('/api/account/backup').json()==backup
  assert client.request('DELETE','/api/account',json={'password':registration['password']},headers=headers).status_code==409
  request=client.post('/api/account/privacy-request',json={'kind':'appeal','message':'Please review my account request.'},headers=headers)
  assert request.status_code==200
  assert client.get('/api/account/privacy-requests').json()['requests'][0]['id']==request.json()['id']
  assert client.post('/api/account/cloud-consent',json={'enabled':False,'notice_version':accounts.VERSION},headers=headers).status_code==200
  assert client.get('/api/account/backup').status_code==403
  with accounts.database() as db:assert db.execute('SELECT COUNT(*) FROM backups').fetchone()[0]==0
  assert len(client.get('/api/account/consents').json()['receipts'])>=3
  assert client.get('/api/account/export').json()['backup'] is None
  assert client.post('/api/auth/forgot-password',json={'email':registration['email']},headers=origin).status_code==200
  reset_token=messages[-1][2]
  assert reset_token!=token
  new_password='another unique long passphrase'
  assert client.post('/api/auth/reset-password',json={'token':reset_token,'password':new_password},headers=origin).status_code==200
  assert client.get('/api/auth/me').status_code==401
  assert client.post('/api/auth/reset-password',json={'token':reset_token,'password':new_password},headers=origin).status_code==400
  assert client.post('/api/auth/login',json={'email':registration['email'],'password':registration['password']},headers=origin).status_code==401
  seed=pyotp.random_base32()
  with accounts.database() as db:db.execute('UPDATE users SET role="staff",mfa_enc=?,plan="free" WHERE id=?',(accounts.encrypt(seed),user_id))
  assert client.post('/api/auth/login',json={'email':registration['email'],'password':new_password},headers=origin).status_code==401
  login=client.post('/api/auth/login',json={'email':registration['email'],'password':new_password,'otp':pyotp.TOTP(seed).now()},headers=origin)
  assert login.status_code==200
  assert client.get('/api/admin/overview').json()['private_entries_accessible'] is False
  headers={**origin,'X-CSRF-Token':login.json()['csrf']}
  assert client.post('/api/admin/requests/'+request.json()['id'],json={'status':'in_review'},headers=headers).status_code==200
  assert client.post('/api/auth/login',json={'email':registration['email'],'password':new_password,'otp':pyotp.TOTP(seed).now()},headers=origin).status_code==401
  assert client.request('DELETE','/api/account',json={'password':new_password},headers=headers).status_code==200
  assert client.get('/api/auth/me').status_code==401
  with accounts.database() as db:
   for table in ['users','sessions','tokens','receipts','backups','requests']:assert db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
  with patch.dict(os.environ,{'AUTH_ENABLED':'false'}):
   assert client.get('/api/auth/config').json()['enabled'] is False
   assert client.post('/api/auth/register',json=registration,headers=origin).status_code==503
print('PASS: consent gates, origin/CSRF, verification, Argon2, encrypted records, resets, revocation, MFA/replay, roles, webhook signatures/idempotency, entitlement, backup withdrawal, privacy requests and deletion')
