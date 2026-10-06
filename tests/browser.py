"""Browser release checks against the built app; no real personal data or messages."""
from pathlib import Path
from urllib.parse import urlsplit
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
import json
import time
from playwright.sync_api import sync_playwright, expect
root=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        clean=urlsplit(path).path
        if clean.startswith('/healthapp/'):
            clean=clean[len('/healthapp/'):]
        else:
            clean=clean.lstrip('/')
        return str(root/'dist'/clean)
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:8765/healthapp/'
def stored(page,key):
    return page.evaluate('''async key=>{const request=indexedDB.open('healthup',1);const db=await new Promise((resolve,reject)=>{request.onsuccess=()=>resolve(request.result);request.onerror=reject});return await new Promise((resolve,reject)=>{const r=db.transaction(key).objectStore(key).get('current');r.onsuccess=()=>resolve(r.result);r.onerror=reject})}''',key)
def wait_stored(page,key,predicate):
    for _ in range(50):
        value=stored(page,key)
        if predicate(value): return value
        page.wait_for_timeout(100)
    raise AssertionError(f'Persistence check failed: {key}: {value}')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['notifications'])
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(url,wait_until='networkidle')
    expect(page.locator('.landing-hero h1')).to_contain_text('Balance your life')
    page.screenshot(path=str(root/'tests/landing-desktop.png'),full_page=True)
    page.locator('.landing-header .button').click()
    page.get_by_label('Your name, if you’d like').fill('Alex')
    page.get_by_role('button',name='Start my HealthUp').click()
    expect(page.locator('.page-heading h1')).to_contain_text('Alex')
    page.get_by_role('button',name='+ 237 ml',exact=True).click()
    wait_stored(page,'hydration',lambda x:len(x or [])==1)
    expect(page.locator('.water-stat strong')).to_contain_text('237')
    page.get_by_role('button',name='+ Meal',exact=True).click()
    page.get_by_label('What did you have?').fill('A nourishing lunch')
    page.locator('dialog button[type=submit]').click()
    wait_stored(page,'meals',lambda x:len(x or [])==1)
    page.reload(wait_until='networkidle')
    expect(page.locator('.water-stat strong')).to_contain_text('237')
    expect(page.locator('.app-main')).to_contain_text('A nourishing lunch')
    print('PASS: onboarding, water, meal, IndexedDB persistence',flush=True)
    page.get_by_role('button',name='+ Mood',exact=True).click()
    page.get_by_role('button',name='Good',exact=True).click()
    page.get_by_role('button',name='Continue',exact=True).click()
    page.get_by_label('Anything you want to remember?').fill('A quiet moment helped.')
    page.get_by_role('button',name='Save check-in').click()
    wait_stored(page,'moods',lambda x:len(x or [])==1)
    page.locator('.sidebar nav').get_by_role('button',name='Settings',exact=True).click()
    page.get_by_label('Show optional weight features').check()
    page.get_by_role('button',name='Enable notifications').click()
    wait_stored(page,'notification_preferences',lambda x:x and x['enabled'])
    page.locator('.sidebar nav').get_by_role('button',name='Today',exact=True).click()
    page.get_by_role('button',name='+ Weight',exact=True).click()
    page.get_by_label('Weight (kg)').fill('72.5')
    page.locator('dialog button[type=submit]').click()
    wait_stored(page,'weight_entries',lambda x:len(x or [])==1)
    page.locator('.sidebar nav').get_by_role('button',name='Your progress').click()
    expect(page.locator('.weight-panel')).to_contain_text('72.5')
    expect(page.locator('.mood-history')).to_contain_text('Mostly happy')
    print('PASS: mood quiz, weight, preferences, notification permission, history',flush=True)
    page.locator('.sidebar nav').get_by_role('button',name='Food & recipes').click()
    expect(page.locator('.recipe-card')).to_have_count(100)
    page.get_by_role('textbox',name='Search recipes').fill('blueberry balance')
    expect(page.locator('.recipe-card')).to_have_count(1)
    page.get_by_role('button',name='Open Blueberry Balance Bowl').click()
    original=page.locator('.nutrition-strip strong').first.inner_text()
    page.get_by_label('Swap Plain Greek yogurt').select_option('cottage')
    assert page.locator('.nutrition-strip strong').first.inner_text()!=original
    page.get_by_role('button',name='Prep mode',exact=True).click()
    page.get_by_label('Complete cooking step 1').check()
    expect(page.locator('.instructions .step-done')).to_have_count(1)
    page.get_by_role('button',name='Favorite recipe',exact=True).click()
    page.get_by_role('button',name='Close dialog',exact=True).click()
    page.get_by_role('textbox',name='Search recipes').fill('')
    page.get_by_role('button',name='Keep my favorites').click()
    expect(page.locator('.recipe-card')).to_have_count(1)
    page.get_by_label('Search USDA foods').fill('yogurt')
    page.get_by_role('button',name='Look up',exact=True).click()
    expect(page.locator('.live-lookup')).to_contain_text('USDA is unavailable')
    print('PASS: 100 recipes, search, swap estimates, prep mode, favorites, API fallback',flush=True)
    page.locator('.sidebar nav').get_by_role('button',name='100-day journey').click()
    expect(page.locator('.journey-tile')).to_have_count(100)
    page.locator('.journey-tile').last.click()
    page.get_by_role('button',name='Mark explored',exact=True).click()
    wait_stored(page,'journey',lambda x:x and 100 in x['completed'])
    expect(page.locator('.journey-tile.completed')).to_have_count(1)
    page.locator('.sidebar nav').get_by_role('button',name='Calendar',exact=True).click()
    page.get_by_role('button',name='Add event',exact=True).click()
    page.get_by_label('Title',exact=True).fill('Gentle walk')
    page.get_by_label('Repeat',exact=True).select_option('daily')
    page.locator('dialog button[type=submit]').click()
    wait_stored(page,'calendar_events',lambda x:len(x or [])==1)
    expect(page.locator('.agenda')).to_contain_text('Gentle walk')
    page.get_by_role('button',name='Complete Gentle walk',exact=True).click()
    expect(page.locator('.agenda-event.done')).to_have_count(1)
    page.locator('.agenda-title').click()
    page.get_by_label('Title',exact=True).fill('Gentle evening walk')
    page.locator('dialog button[type=submit]').click()
    expect(page.locator('.agenda')).to_contain_text('Gentle evening walk')
    page.get_by_role('button',name='Delete Gentle evening walk for this date',exact=True).click()
    expect(page.locator('.agenda-event')).to_have_count(0)
    event=stored(page,'calendar_events')[0]
    assert event['repeat']=='daily'
    assert len(wait_stored(page,'calendar_events',lambda x:len(x[0]['excluded'])==1)[0]['excluded'])==1
    print('PASS: open journey, calendar create/edit/complete/delete occurrence, recurrence',flush=True)
    page.locator('.sidebar nav').get_by_role('button',name='Mind & moments').click()
    page.get_by_role('button',name='1m',exact=True).click()
    page.get_by_role('button',name='Begin',exact=True).click()
    timer=wait_stored(page,'timer',lambda x:x and x['endsAt']>0)
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('button',name='Pause',exact=True)).to_be_visible()
    assert stored(page,'timer')['endsAt']==timer['endsAt']
    page.get_by_role('button',name='Pause',exact=True).click()
    wait_stored(page,'timer',lambda x:x and x['endsAt']==0)
    page.get_by_role('button',name='Resume',exact=True).click()
    wait_stored(page,'timer',lambda x:x and x['endsAt']>0)
    # Short end-time fixture checks completion without a one-minute blocking wait.
    page.evaluate('''async()=>{const r=indexedDB.open('healthup',1);const db=await new Promise(resolve=>r.onsuccess=()=>resolve(r.result));const tx=db.transaction('timer','readwrite');tx.objectStore('timer').put({endsAt:Date.now()+1000,duration:1,kind:'Test meditation'},'current');await new Promise(resolve=>tx.oncomplete=resolve)}''')
    page.reload(wait_until='networkidle')
    wait_stored(page,'completed_tasks',lambda x:any(t['label']=='Test meditation' for t in (x or [])))
    page.get_by_role('button',name='Begin breathing',exact=True).click()
    expect(page.locator('.breathing-center strong')).not_to_have_text('Begin when you’re ready')
    page.get_by_role('button',name='Choose your pause · 3 questions').click()
    for name in ['A minute','Quiet','Right here']:
        page.get_by_role('button',name=name,exact=True).click()
    expect(page.locator('.quiz-result')).to_contain_text('Take a quiet pause')
    page.get_by_role('button',name='I took this pause',exact=True).click()
    print('PASS: persisted timer, pause/resume, timer completion, breathing, preference quiz',flush=True)
    page.get_by_role('button',name='Botanical pairs',exact=True).click()
    # Reveal accessible pairs using the public game UI; no app state mutation.
    known={}
    moves=0
    while page.locator('.puzzle-grid button.matched').count()<12:
        moves+=1
        assert moves<40,'Puzzle did not converge'
        unmatched=[i for i in range(12) if not page.locator('.puzzle-grid button').nth(i).is_disabled()]
        pairs={}
        for i in unmatched:
            if i in known: pairs.setdefault(known[i],[]).append(i)
        complete=next((ids for ids in pairs.values() if len(ids)==2),None)
        if complete:
            for i in complete: page.locator('.puzzle-grid button').nth(i).click()
            continue
        unknown=[i for i in unmatched if i not in known]
        assert unknown,'No discoverable tiles remain'
        first=unknown[0]
        page.locator('.puzzle-grid button').nth(first).click()
        symbol=page.locator('.puzzle-grid button').nth(first).inner_text()
        known[first]=symbol
        partner=next((i for i in unmatched if i!=first and known.get(i)==symbol),None)
        if partner is not None:
            page.locator('.puzzle-grid button').nth(partner).click()
        else:
            second=next(i for i in unmatched if i!=first and i not in known)
            page.locator('.puzzle-grid button').nth(second).click()
            known[second]=page.locator('.puzzle-grid button').nth(second).inner_text()
            page.wait_for_timeout(1000)
    expect(page.locator('.puzzle-complete')).to_be_visible()
    page.get_by_role('button',name='Save my pause',exact=True).click()
    print('PASS: botanical puzzle',flush=True)
    page.locator('.sidebar nav').get_by_role('button',name='Learn',exact=True).click()
    expect(page.locator('.guide-card')).to_have_count(8)
    page.locator('.guide-card').first.click()
    expect(page.locator('dialog .guide-body')).to_be_visible()
    page.get_by_role('button',name='Close dialog').click()
    page.get_by_role('button',name='Find research',exact=True).click()
    expect(page.locator('.research-panel')).to_contain_text('Research search is unavailable')
    page.locator('.header-actions').get_by_role('button',name='Open Support').click()
    expect(page.locator('dialog')).to_contain_text('Call or text 988')
    expect(page.get_by_role('link',name='Call 988',exact=True)).to_have_attribute('href','tel:988')
    page.keyboard.press('Escape')
    assert page.locator('dialog').count()==0
    page.goto(url+'#today',wait_until='networkidle')
    page.screenshot(path=str(root/'tests/today-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Open quick actions',exact=True).click()
    expect(page.locator('dialog .action-sheet')).to_be_visible()
    page.keyboard.press('Escape')
    page.locator('.mobile-nav').get_by_role('button',name='Calendar',exact=True).click()
    expect(page.locator('.calendar-main')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('.mobile-nav').get_by_role('button',name='Today',exact=True).click()
    page.screenshot(path=str(root/'tests/today-mobile.png'),full_page=True)
    page.emulate_media(reduced_motion='reduce')
    page.locator('.mobile-more').get_by_role('button',name='Mind',exact=True).click()
    assert page.locator('.breathing-orbit').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
    print('PASS: learn, research fallback, support, keyboard dismissal, mobile nav, reduced motion',flush=True)
    page.evaluate('navigator.serviceWorker.ready')
    page.wait_for_function('navigator.serviceWorker.controller!==null')
    context.set_offline(True)
    page.goto(url+'#food',wait_until='domcontentloaded')
    expect(page.locator('.recipe-card')).to_have_count(100)
    expect(page.locator('.offline-badge')).to_be_visible()
    expect(page.locator('.brand:visible img').first).to_be_visible()
    page.locator('.mobile-nav').get_by_role('button',name='Today',exact=True).click()
    expect(page.locator('.water-stat strong')).to_contain_text('237')
    assert not errors,errors
    print('PASS: offline startup, cached 100 recipes, persisted personal data, no console exceptions',flush=True)
    browser.close()
server.shutdown()
