from pathlib import Path
from urllib.parse import urlsplit
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
 def translate_path(self,path):
  return str(root/'dist'/urlsplit(path).path.removeprefix('/healthapp/'))
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8766),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
failures=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.goto('http://127.0.0.1:8766/healthapp/#landing',wait_until='networkidle')
 page.locator('.landing-header .button').click()
 page.get_by_label('I am 18 or older.',exact=True).check()
 page.get_by_label('I acknowledge the wellness purpose and privacy notice; local entries are not monitored.',exact=True).check()
 page.get_by_role('button',name='Start my HealthUp').click()
 for route in ['landing','today','calendar','food','journey','mind','progress','learn','settings','studio','journal','resources','privacy','account','staff']:
  page.goto(f'http://127.0.0.1:8766/healthapp/#{route}',wait_until='networkidle')
  page.locator('main').wait_for()
  if route=='food': page.locator('.recipe-card').first.wait_for()
  page.add_script_tag(path=str(root/'node_modules/axe-core/axe.min.js'))
  result=page.evaluate('''async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})''')
  for violation in result['violations']:
   failures.append({'route':route,'id':violation['id'],'impact':violation['impact'],'nodes':[n['target'] for n in violation['nodes']][:5]})
  print(f'Checked accessibility: {route}',flush=True)
 browser.close()
server.shutdown()
assert not failures,failures
print('PASS: automated WCAG A/AA checks on fifteen screens. Manual/device review remains useful.')
