import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    assert client.get('/api/health').json()=={'status':'ok','product':'HealthUp'}
    assert len(client.get('/api/recipes').json()['recipes'])==100
    assert client.get('/api/events').json()['storage']=='local-first'
    assert client.get('/api/content').json()['product']=='HealthUp'
    assert client.get('/api/foods/search?q=a').status_code==422
    preflight=client.options('/api/research',headers={'Origin':'https://tastythaicorp.github.io','Access-Control-Request-Method':'GET'})
    assert preflight.status_code==200
    assert preflight.headers['access-control-allow-origin']=='https://tastythaicorp.github.io'
    async def fail(*args,**kwargs):
        raise main.HTTPException(503,'Service unavailable')
    original=main.fetch_json
    main.fetch_json=fail
    assert client.get('/api/foods/search?q=test-failure').status_code==503
    assert client.get('/api/research?q=test-failure').status_code==503
    async def fixture(url,params):
        if 'esearch' in url:
            return {'esearchresult':{'idlist':['40301581']}}
        return {'result':{'40301581':{'title':'Fixture title','authors':[{'name':'Test author'}],
            'fulljournalname':'Test journal','pubdate':'2025','articleids':[{'idtype':'doi','value':'10.test/fixture'}]}}}
    main.fetch_json=fixture
    result=client.get('/api/research?q=fixture').json()['papers'][0]
    assert result['pmid']=='40301581'
    assert result['doi']=='10.test/fixture'
    assert result['url']=='https://pubmed.ncbi.nlm.nih.gov/40301581/'
    main.fetch_json=original
    assert client.get('/api/missing').status_code==404
print('PASS: health, 100 recipes, public content, local-only events, query validation, CORS, API failures, real metadata mapping, 404')
