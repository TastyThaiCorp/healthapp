from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit
import threading
from playwright.sync_api import sync_playwright,expect
root=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
 def translate_path(self,path):return str(root/'dist'/urlsplit(path).path.removeprefix('/healthapp/'))
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8767),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=b.new_page()
  page.goto('http://127.0.0.1:8767/healthapp/?brand=organic-ascent#landing',wait_until='networkidle')
  page.evaluate("""async()=>{const cache=await caches.open('healthup-wellness-v3');await cache.put('/healthapp/assets/healthup-logo.png',new Response('old logo'));await cache.put('/healthapp/index.html',new Response('<p>Old shell</p>'))}""")
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000)
  page.reload(wait_until='networkidle')
  image=page.locator('.landing-header .brand img')
  expect(image).to_have_attribute('src','/healthapp/assets/healthup-organic-ascent.png')
  assert image.evaluate('(e)=>e.complete&&e.naturalWidth===2172')
  page.context.set_offline(True)
  page.reload(wait_until='domcontentloaded')
  expect(image).to_be_visible()
  assert image.evaluate('(e)=>e.complete&&e.naturalWidth===2172')
  print('PASS: stale cached branding cannot replace new logo, including offline startup')
  b.close()
finally:server.shutdown()
