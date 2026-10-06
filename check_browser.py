import threading
import json
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parent
server=ThreadingHTTPServer(('127.0.0.1',8765),partial(SimpleHTTPRequestHandler,directory=str(root/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8765',wait_until='networkidle')
 page.locator('#featured-products .product-card').first.wait_for()
 page.screenshot(path=str(root/'preview-desktop.png'),full_page=True)
 page.locator('nav a[href="#catalog"]').click()
 assert page.locator('#products .product-card').count()==10
 page.locator('[data-filter="python"]').click()
 assert page.locator('#products .product-card').count()==5
 page.locator('#products .product-card').first.click()
 assert page.locator('[data-page="product"]').is_visible()
 page.go_back()
 assert page.locator('[data-page="catalog"]').is_visible()
 page.goto('http://127.0.0.1:8765/#contact',wait_until='networkidle')
 page.locator('#name').fill('Demo Tester')
 page.locator('#email').fill('tester@example.com')
 page.locator('#message').fill('Testing the HealthUp foundation inquiry.')
 page.locator('.consent input').check()
 page.locator('button[type="submit"]').click()
 assert page.locator('#toast').evaluate('(el)=>el.classList.contains("show")')
 assert page.evaluate('JSON.parse(localStorage.getItem("healthup-inquiry")).name')=='Demo Tester'
 assert page.locator('#name').input_value()==''
 page.goto('http://127.0.0.1:8765/#privacy',wait_until='networkidle')
 page.locator('#delete-inquiry').click()
 assert page.evaluate('localStorage.getItem("healthup-inquiry")') is None
 page.set_viewport_size({'width':390,'height':844})
 page.goto('http://127.0.0.1:8765/#home',wait_until='networkidle')
 page.locator('#menu-toggle').click()
 assert page.locator('#menu-toggle').get_attribute('aria-expanded')=='true'
 page.locator('nav a[href="#catalog"]').click()
 page.wait_for_function('document.querySelector("#menu-toggle").getAttribute("aria-expanded") === "false"')
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.screenshot(path=str(root/'preview-mobile.png'),full_page=True)
 assert not errors,errors
 # Test online mode without delivering any real inquiry.
 page.route('**/config.js',lambda r:r.fulfill(content_type='application/javascript',body="window.HEATHUP_CONFIG={apiBaseUrl:'https://api.healthup.test'};"))
 attempts=[]
 def api_mock(route):
  payload=route.request.post_data_json
  attempts.append(payload)
  if len(attempts)==1:
   route.fulfill(status=503,content_type='application/json',body='{"detail":"Unavailable"}',headers={'Access-Control-Allow-Origin':'*'})
  else:
   route.fulfill(status=201,content_type='application/json',body=json.dumps({'status':'received','inquiry_id':payload['request_id']}),headers={'Access-Control-Allow-Origin':'*'})
 page.route('https://api.healthup.test/api/integrate',api_mock)
 page.goto('http://127.0.0.1:8765/#contact',wait_until='networkidle')
 page.reload(wait_until='networkidle')
 page.locator('#name').fill('Online Tester')
 page.locator('#email').fill('online@example.com')
 page.locator('#message').fill('Test meaningful online inquiry delivery.')
 page.locator('.consent input').check()
 page.locator('button[type="submit"]').click()
 page.wait_for_function('!document.querySelector("button[type=submit]").disabled')
 assert page.locator('#name').input_value()=='Online Tester'
 assert page.locator('#toast-title').inner_text()=='Your inquiry is still in the form.'
 page.locator('button[type="submit"]').click()
 page.wait_for_function('document.querySelector("#name").value === ""')
 assert attempts[0]['request_id']==attempts[1]['request_id']
 assert page.locator('#toast-title').inner_text()=='Your inquiry was received.'
 assert not errors,errors
 browser.close()
server.shutdown()
print('PASS: catalog, filters, product routing, history, inquiry save/reset/delete, mobile menu, overflow, online failure recovery, online success, retry identity, no JS errors')
