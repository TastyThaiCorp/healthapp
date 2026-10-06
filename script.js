'use strict';
(() => {
  const $ = (selector) => document.querySelector(selector);
  const pages = [...document.querySelectorAll('[data-page]')];
  const menu = $('#navigation');
  const toggle = $('#menu-toggle');
  let products = [], filter = 'all', toastTimer;
  const icons = () => window.lucide?.createIcons();
  const imageStyle = (index) => `background-position:${(index % 5) * 25}% ${index < 5 ? 0 : 100}%`;
  const escape = (text) => String(text).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function card(p) {
    return `<a class="product-card" href="#product/${p.id}" aria-label="Explore ${escape(p.name)}"><div class="product-art" style="${imageStyle(p.image)}" role="img" aria-label="${escape(p.name)} conceptual still-life artwork"><span class="product-number">${String(p.image + 1).padStart(2,'0')} / LAB</span></div><span class="eyebrow">${p.category === 'python' ? 'PYTHON' : 'TYPESCRIPT'} / ${escape(p.focus.toUpperCase())}</span><h3>${escape(p.name)} <span aria-hidden="true">→</span></h3><p>${escape(p.tagline)}</p><span class="concept-label">IN DEVELOPMENT · PRODUCT CONCEPT</span></a>`;
  }
  function closeMenu() { menu.classList.remove('open'); toggle.setAttribute('aria-expanded','false'); toggle.setAttribute('aria-label','Open navigation'); }
  toggle.addEventListener('click', () => { const open = !menu.classList.contains('open'); menu.classList.toggle('open',open); toggle.setAttribute('aria-expanded',String(open)); toggle.setAttribute('aria-label',open ? 'Close navigation' : 'Open navigation'); });
  document.addEventListener('keydown', (e) => { if(e.key === 'Escape') { closeMenu(); toggle.focus(); } });
  document.addEventListener('click', (e) => { if(!e.target.closest('header')) closeMenu(); });
  const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => entries.forEach(entry => { if(entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); } }), {threshold:0.08}) : null;
  function reveal() { document.querySelectorAll('.product-card,.principles article').forEach(el => { if(!observer) return; el.classList.add('reveal'); observer.observe(el); }); }
  function renderCatalog() { const selected = products.filter(p => filter === 'all' || p.category === filter); $('#products').innerHTML = selected.map(card).join(''); $('#result-count').textContent = `${selected.length} concepts`; reveal(); }
  function route() {
    const [requested, id] = location.hash.slice(1).split('/');
    let page = requested || 'home';
    if(!pages.some(p => p.dataset.page === page)) page = 'home';
    if(page === 'product') {
      const p = products.find(p => p.id === id);
      if(!p) { page = 'catalog'; }
      else $('#product-detail').innerHTML = `<a href="#catalog" class="back-link">← Back to the product lab</a><div class="detail-layout"><div class="product-art" style="${imageStyle(p.image)}" role="img" aria-label="${escape(p.name)} conceptual artwork"></div><div class="detail-copy"><span class="eyebrow">CONCEPT ${String(p.image+1).padStart(2,'0')} / ${escape(p.focus.toUpperCase())}</span><h1>${escape(p.name)}</h1><p>${escape(p.tagline)}</p><p>${escape(p.description)}</p><dl class="specs"><div><dt>Foundation</dt><dd>${p.category === 'python' ? 'Python' : 'TypeScript'}</dd></div><div><dt>Status</dt><dd>Product concept</dd></div><div><dt>Availability</dt><dd>Not yet released</dd></div></dl><a class="button light" href="#contact">Discuss this concept →</a></div></div>`;
    }
    pages.forEach(el => { el.hidden = el.dataset.page !== page; });
    menu.querySelectorAll('a').forEach(a => { if(a.hash === `#${page === 'product' ? 'catalog' : page}`) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
    const titles = {home:'Naturally precise. Thoughtfully built.',catalog:'Product lab',foundations:'Our foundations',contact:'Start a conversation',privacy:'Privacy',product:products.find(p=>p.id===id)?.name};
    document.title = `HealthUp — ${titles[page]}`;
    closeMenu(); window.scrollTo({top:0,behavior:'instant'}); $('#main').focus({preventScroll:true}); reveal(); icons();
  }
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed',String(b === button))); renderCatalog(); }));
  function toast(title,message) { clearTimeout(toastTimer); $('#toast-title').textContent=title; $('#toast-message').textContent=message; $('#toast').classList.add('show'); toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),6500); }
  $('#toast-close').addEventListener('click',()=>$('#toast').classList.remove('show'));
  const apiBase = String(window.HEATHUP_CONFIG?.apiBaseUrl || '').trim().replace(/\/$/, '');
  let pendingRequest = null;
  const online = Boolean(apiBase);
  $('#delivery-note').textContent = online
    ? 'Your inquiry will be sent to HealthUp and stored for up to 30 days. No email notification is promised.'
    : 'Online delivery is not connected yet. Save a draft on this device, then download it from Privacy.';
  $('#delivery-consent').textContent = online
    ? 'I agree to send this inquiry to HealthUp for storage and review.'
    : 'I understand this draft is saved only on this device.';
  const submit = $('#contact-form button[type="submit"]');
  submit.innerHTML = online ? 'Send inquiry <span>→</span>' : 'Save local draft <span>→</span>';
  $('#form-delivery-status').textContent = online ? 'Submitted information is stored for up to 30 days.' : 'No message is sent to a server.';
  $('#contact-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if(submit.disabled || !form.reportValidity()) return;
    const values = Object.fromEntries(new FormData(form));
    if(!online) {
      try {
        localStorage.setItem('healthup-inquiry',JSON.stringify({...values,savedAt:new Date().toISOString()}));
        form.reset(); toast('Your draft is saved locally.','No message was sent. Download your copy from Privacy.');
      } catch { toast('Your draft could not be saved.','Browser storage is unavailable. Your form has been kept intact.'); }
      return;
    }
    const initialLabel = submit.innerHTML;
    submit.disabled = true; submit.textContent = 'Sending inquiry…';
    form.setAttribute('aria-busy','true');
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(),60000);
    try {
      const endpoint = new URL(apiBase);
      if(endpoint.protocol !== 'https:' && !['localhost','127.0.0.1'].includes(endpoint.hostname)) throw new Error('Configuration error');
      const fields = {name:values.name,email:values.email,brief:values.message,interest:values.interest,website:values.website || ''};
      const fingerprint = JSON.stringify(fields);
      if(!pendingRequest || pendingRequest.fingerprint !== fingerprint) pendingRequest = {fingerprint,id:crypto.randomUUID()};
      const response = await fetch(`${apiBase}/api/integrate`, {
        method:'POST', headers:{'Content-Type':'application/json','Accept':'application/json'},
        body:JSON.stringify({...fields,request_id:pendingRequest.id}), signal:controller.signal,
        credentials:'omit', redirect:'error'
      });
      const result = await response.json().catch(()=>null);
      if(!response.ok || result?.status !== 'received' || result.inquiry_id !== pendingRequest.id) {
        const messages = {422:'Check your details. The message must contain at least 10 characters.',429:'Too many inquiries. Please try again in an hour.',403:'This website origin has not been enabled for the API.'};
        throw new Error(messages[response.status] || 'The server could not confirm your inquiry. Please try again.');
      }
      form.reset(); pendingRequest = null;
      toast('Your inquiry was received.','It has been saved by HealthUp. Thank you for sharing your idea.');
    } catch(error) {
      toast('Your inquiry is still in the form.', error.name === 'AbortError'
        ? 'The request timed out. Retry to confirm delivery without creating a duplicate.'
        : error instanceof TypeError ? 'Unable to reach the API. Check your connection and try again.' : error.message);
    } finally { clearTimeout(timeout); submit.disabled=false; submit.innerHTML=initialLabel; form.removeAttribute('aria-busy'); }
  });
  $('#download-inquiry').addEventListener('click', () => {
    try {
      const stored = localStorage.getItem('healthup-inquiry');
      if(!stored) return toast('No saved inquiry.','Save an inquiry on the Connect page first.');
      const blob = new Blob([stored],{type:'application/json'}), url=URL.createObjectURL(blob), a=document.createElement('a');
      a.href=url; a.download='healthup-inquiry.json'; document.body.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch { toast('Download unavailable.','Browser storage could not be accessed.'); }
  });
  $('#delete-inquiry').addEventListener('click',()=> { try { localStorage.removeItem('healthup-inquiry'); toast('Local inquiry deleted.','The saved copy has been removed from this browser.'); } catch { toast('Deletion unavailable.','Browser storage could not be accessed.'); } });
  $('#year').textContent=new Date().getFullYear();
  window.addEventListener('hashchange',route);
  fetch('products.json').then(r=> { if(!r.ok) throw new Error('Catalog unavailable'); return r.json(); }).then(data=> { products=data; renderCatalog(); $('#featured-products').innerHTML=products.slice(0,3).map(card).join(''); route(); }).catch(()=> { $('#products').textContent='The product lab could not load. Please refresh or try again later.'; route(); });
  icons();
})();
