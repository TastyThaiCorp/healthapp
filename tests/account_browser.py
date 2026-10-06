"""Browser account lifecycle against the real API with fixture-only email delivery.
Build first: VITE_BASE_PATH=/ VITE_API_URL=same-origin npm run build -- --outDir /tmp/healthup-account-dist
Requires backend requirements + Playwright in the Python environment.
"""
import os,sys,tempfile,threading,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from cryptography.fernet import Fernet
from playwright.sync_api import sync_playwright,expect
import uvicorn
base='http://127.0.0.1:8768'
with tempfile.TemporaryDirectory() as folder:
 env={'AUTH_ENABLED':'true','HEALTHUP_LEGAL_REVIEWED':'true','ACCOUNT_DB_PATH':folder+'/accounts.sqlite3',
 'ACCOUNT_ENCRYPTION_KEYS':Fernet.generate_key().decode(),'ACCOUNT_HASH_KEY':'fixture-key-'+('x'*40),
 'HEALTHUP_COMPANY_NAME':'Browser test operator','HEALTHUP_PRIVACY_EMAIL':'privacy@example.com','APP_URL':base,
 'SMTP_HOST':'fixture','SMTP_USER':'fixture','SMTP_PASSWORD':'fixture','SMTP_FROM':'test@example.com','HEALTHUP_ENV':'test',
 'HEALTHUP_FRONTEND_DIST':'/tmp/healthup-account-dist'}
 with patch.dict(os.environ,env):
  import main,accounts
  messages=[]
  def mail(address,kind,token):messages.append((address,kind,token))
  with patch.object(accounts,'mail',mail):
   server=uvicorn.Server(uvicorn.Config(main.app,host='127.0.0.1',port=8768,log_level='error',access_log=False))
   thread=threading.Thread(target=server.run,daemon=True);thread.start()
   for _ in range(100):
    if server.started:break
    time.sleep(.05)
   try:
    with sync_playwright() as p:
     browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
     context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();errors=[]
     page.on('pageerror',lambda error:errors.append(str(error)))
     page.goto(base+'/#landing',wait_until='networkidle')
     page.locator('.landing-header .button').click()
     expect(page.locator('.account-form')).to_be_visible()
     page.get_by_role('button',name='Register',exact=True).click()
     page.get_by_label('Email',exact=True).fill('first@example.com')
     page.get_by_label('Password',exact=True).fill('first unique long passphrase')
     page.get_by_label('Display name',exact=True).fill('First person')
     page.locator('.account-form input[type=checkbox]').evaluate_all('(inputs)=>inputs.forEach(i=>i.click())')
     page.get_by_label('Type your name to acknowledge',exact=True).fill('First person')
     page.get_by_role('button',name='Create my account',exact=True).click()
     expect(page.locator('.notice')).to_contain_text('verification email')
     assert messages[0][0]=='first@example.com'
     response=context.request.post(base+'/api/auth/verify',data={'token':messages[0][2]},headers={'Origin':base})
     assert response.status==200
     page.get_by_role('button',name='Sign in',exact=True).first.click()
     page.get_by_label('Email',exact=True).fill('first@example.com')
     page.get_by_label('Password',exact=True).fill('first unique long passphrase')
     page.locator('.account-form button[type=submit]').click()
     expect(page.locator('dialog')).to_contain_text('How are you feeling today?')
     expect(page.locator('dialog')).to_contain_text('It’s okay to not feel okay')
     page.get_by_role('button',name='Close dialog',exact=True).click()
     expect(page.locator('dialog')).to_be_visible()
     page.get_by_role('button',name='Prefer not to say · continue privately',exact=True).click()
     expect(page.locator('dialog')).to_have_count(0)
     expect(page.locator('.page-heading h1')).to_contain_text('First person')
     page.get_by_role('button',name='+ 237 ml',exact=True).click()
     expect(page.locator('.water-stat strong')).to_contain_text('237')
     page.locator('.sidebar nav').get_by_role('button',name='Your account',exact=True).click()
     expect(page.locator('.app-main')).to_contain_text('first@example.com')
     page.get_by_label('I explicitly choose server processing/storage of my wellness export for backup and restore.',exact=True).check()
     expect(page.get_by_label('I explicitly choose server processing/storage of my wellness export for backup and restore.',exact=True)).to_be_checked()
     expect(page.get_by_role('button',name='Save encrypted cloud backup',exact=True)).to_be_disabled()
     page.get_by_label('I explicitly choose server processing/storage of my wellness export for backup and restore.',exact=True).uncheck()
     expect(page.get_by_role('button',name='Save encrypted cloud backup',exact=True)).to_be_disabled()
     print('PASS: registration, acknowledgements, verification, mandatory post-login prompt with private skip, optional sharing declined without losing tools',flush=True)
     page.get_by_role('button',name='Sign out',exact=True).click()
     expect(page.locator('.account-form')).to_be_visible()
     # Create a second verified account through the same real API.
     registration={'email':'second@example.com','password':'second unique long passphrase','name':'Second person','country':'US','adult':True,'terms':True,'essential_consent':True,'wellness_ack':True,'signed_name':'Second person','notice_version':accounts.VERSION}
     assert context.request.post(base+'/api/auth/register',data=registration,headers={'Origin':base}).status==200
     assert context.request.post(base+'/api/auth/verify',data={'token':messages[-1][2]},headers={'Origin':base}).status==200
     page.get_by_label('Email',exact=True).fill('second@example.com')
     page.get_by_label('Password',exact=True).fill('second unique long passphrase')
     page.locator('.account-form button[type=submit]').click()
     expect(page.locator('dialog')).to_contain_text('How are you feeling today?')
     page.get_by_role('button',name='Good',exact=True).click()
     page.get_by_role('button',name='Continue',exact=True).click()
     page.get_by_role('button',name='Save check-in',exact=True).click()
     expect(page.locator('dialog')).to_have_count(0)
     expect(page.locator('.page-heading h1')).to_contain_text('Second person')
     expect(page.locator('.water-stat strong')).to_contain_text('0')
     page.locator('.sidebar nav').get_by_role('button',name='Your account',exact=True).click()
     page.get_by_role('button',name='Sign out',exact=True).click()
     expect(page.locator('.account-form')).to_be_visible()
     page.get_by_label('Email',exact=True).fill('first@example.com')
     page.get_by_label('Password',exact=True).fill('first unique long passphrase')
     page.locator('.account-form button[type=submit]').click()
     # Every fresh login should show the prompt, even if today's acknowledgement exists.
     expect(page.locator('dialog')).to_contain_text('How are you feeling today?')
     page.get_by_role('button',name='Prefer not to say · continue privately',exact=True).click()
     expect(page.locator('.water-stat strong')).to_contain_text('237')
     print('PASS: account-scoped encrypted device data, private entries isolated, prior account restored, check-in on each login',flush=True)
     assert not errors,errors
     browser.close()
   finally:
    server.should_exit=True;thread.join(timeout=5)
