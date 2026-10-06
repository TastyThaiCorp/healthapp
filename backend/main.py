"""HealthUp public content adapters. Personal health logs remain browser-local."""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent
app = FastAPI(title='HealthUp', docs_url='/api/docs', openapi_url='/api/openapi.json')
origins = [o.strip().rstrip('/') for o in os.getenv('ALLOWED_ORIGINS', 'https://tastythaicorp.github.io').split(',') if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=['GET'], allow_headers=['Accept', 'Content-Type'], max_age=600)
cache: dict[str, tuple[float, Any]] = {}
locks: dict[str, asyncio.Lock] = {}
entrez_lock = asyncio.Lock()
entrez_next = 0.0


@app.middleware('http')
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


def bundled(name):
    return json.loads((ROOT / 'data' / name).read_text())


async def fetch_json(url, params):
    async with httpx.AsyncClient(timeout=7, follow_redirects=False) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Live service unavailable. Cached and bundled content remain available.') from None


async def cached(key, loader):
    if key in cache and cache[key][0] > time.time():
        return cache[key][1]
    # Limit memory by expiring old entries and bounding the query cache.
    for expired in [k for k, v in cache.items() if v[0] < time.time()]:
        cache.pop(expired, None)
    if len(cache) >= 128:
        cache.pop(next(iter(cache)))
    data = await loader()
    cache[key] = (time.time() + 3600, data)
    return data


@app.get('/api/health')
def health():
    return {'status': 'ok', 'product': 'HealthUp'}


@app.get('/api/recipes')
def recipes():
    return bundled('recipes.json')


@app.get('/api/content')
def content():
    return bundled('content.json')


@app.get('/api/events')
def events():
    return {'storage': 'local-first', 'types': ['Meal', 'Water', 'Meditation', 'Movement', 'Self-care',
            'Weigh-in', 'Bedtime', 'Grocery', 'Meal prep', 'Reflection', 'Custom'],
            'message': 'Personal events are stored in your browser. This endpoint supplies event types only.'}


@app.get('/api/foods/search')
async def food_search(q: str = Query(min_length=2, max_length=100)):
    key = os.getenv('USDA_API_KEY')
    if not key:
        if os.getenv('RAILWAY_ENVIRONMENT_ID'):
            raise HTTPException(503, 'Nutrient lookup is not configured. Bundled estimates are available.')
        key = 'DEMO_KEY'
    async def load():
        data = await fetch_json('https://api.nal.usda.gov/fdc/v1/foods/search',
                                {'api_key': key, 'query': q, 'pageSize': 8})
        return {'source': 'USDA FoodData Central', 'foods': [{
            'fdcId': food.get('fdcId'), 'description': food.get('description'),
            'dataType': food.get('dataType'), 'nutrients': food.get('foodNutrients', [])
        } for food in data.get('foods', [])]}
    return await cached('food:' + q.lower(), load)


async def entrez(endpoint, params):
    global entrez_next
    async with entrez_lock:
        # One worker; conservatively keep requests below three per second.
        await asyncio.sleep(max(0, entrez_next - time.monotonic()))
        entrez_next = time.monotonic() + 0.4
        values = {'retmode': 'json', 'tool': 'HealthUp', **params}
        if os.getenv('NCBI_EMAIL'):
            values['email'] = os.environ['NCBI_EMAIL']
        if os.getenv('NCBI_API_KEY'):
            values['api_key'] = os.environ['NCBI_API_KEY']
        return await fetch_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/' + endpoint, values)


@app.get('/api/research')
async def research(q: str = Query(min_length=2, max_length=150)):
    async def load():
        found = await entrez('esearch.fcgi', {'db': 'pubmed', 'term': q, 'retmax': 6, 'sort': 'relevance'})
        ids = found.get('esearchresult', {}).get('idlist', [])
        if not ids:
            return {'source': 'PubMed', 'papers': []}
        result = await entrez('esummary.fcgi', {'db': 'pubmed', 'id': ','.join(ids)})
        metadata = result.get('result', {})
        papers = []
        for pmid in ids:
            entry = metadata.get(pmid, {})
            doi = next((i['value'] for i in entry.get('articleids', []) if i.get('idtype') == 'doi'), None)
            papers.append({'pmid': pmid, 'title': entry.get('title', ''),
                           'authors': [a['name'] for a in entry.get('authors', [])],
                           'journal': entry.get('fulljournalname', ''), 'year': entry.get('pubdate', ''),
                           'doi': doi, 'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'})
        return {'source': 'PubMed', 'papers': papers}
    return await cached('research:' + q.lower(), load)


@app.exception_handler(404)
async def missing(request, error):
    return JSONResponse({'detail': 'This resource was not found. HealthUp local tools remain available.'}, 404)

static = ROOT.parent / 'dist'
if static.is_dir():
    app.mount('/', StaticFiles(directory=static, html=True), name='frontend')
