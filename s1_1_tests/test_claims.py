import copy,json,os
from pathlib import Path
import pytest
from causalverse.evidence_s1.service import EvidenceService

@pytest.fixture(scope='module')
def real():
    s=EvidenceService(Path(os.environ['S1_ACCEPTANCE'])/'claims_runtime')
    contexts={}
    for chain in ('D3','D511'):
        c=next(c for c in s.catalog() if c['chain']==chain)
        contexts[chain]=s.create(dict(selection_id=c['selection_id'],as_of=5400,window=1800),'owner')
    return s,contexts

def request(s,c,semantic=None):
    cat=s.fact_catalog(c['context_id'],'owner')
    f=next(f for f in cat['facts'] if f['semantic']==(semantic or 'SCORE_NOT_PROBABILITY'))
    ref={k:f[k] for k in ('fact_id','evidence_id','payload_sha256')}
    return dict(schema_version=cat['schema_version'],context_id=c['context_id'],snapshot_sha256=cat['snapshot_sha256'],
                claims=[dict(claim_id='c1',claim_type='FACT',evidence_refs=[ref])]),f

def test_real_fact_backfill(real):
    s,contexts=real;r,f=request(s,contexts['D3'])
    out=s.resolve_claims(r,'owner')
    assert out['claims'][0]['facts'][0]==f
    assert f['semantic']=='SCORE_NOT_PROBABILITY' and not out['optimization_allowed']
    (Path(os.environ['S1_ACCEPTANCE'])/'resolved_real_claim.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')

@pytest.mark.parametrize('attack', ['forged_evidence','forged_fact','cross_context','forged_hash','invented_value','probability','root_cause','future_observation','optimization','supported_authorized','free_text','extra_pointer','wrong_snapshot','duplicate_claim','bad_relation','uncomparable'])
def test_attacks_rejected(real,attack):
    s,contexts=real;r,_=request(s,contexts['D3']);c=r['claims'][0];ref=c['evidence_refs'][0]
    if attack=='forged_evidence':ref['evidence_id']='0'*32
    elif attack=='forged_fact':ref['fact_id']='0'*64
    elif attack=='cross_context':r['context_id']=contexts['D511']['context_id'];r['snapshot_sha256']=s.index[r['context_id']]['snapshot_sha256']
    elif attack=='forged_hash':ref['payload_sha256']='0'*64
    elif attack=='wrong_snapshot':r['snapshot_sha256']='0'*64
    elif attack=='invented_value':c['value']=999
    elif attack=='optimization':c['optimization_allowed']=True
    elif attack=='supported_authorized':c['claim_type']='OPTIMIZATION_AUTHORIZED'
    elif attack=='probability':c['claim_type']='FAULT_PROBABILITY'
    elif attack=='root_cause':c['claim_type']='CONFIRMED_PHYSICAL_ROOT_CAUSE'
    elif attack=='future_observation':c['claim_type']='FUTURE_OBSERVATION'
    elif attack=='free_text':c['explanation']='概率80%，已确定根因，可执行控制'
    elif attack=='extra_pointer':ref['pointer']='/future_truth'
    elif attack=='duplicate_claim':r['claims'].append(copy.deepcopy(c))
    elif attack=='bad_relation':c.update(claim_type='RELATION',relation_level='CERTAIN')
    elif attack=='uncomparable':c.update(claim_type='COMPARISON',comparison_basis='DIFFERENCE');c['evidence_refs']*=2
    with pytest.raises((ValueError,PermissionError)):s.resolve_claims(r,'owner')

@pytest.mark.parametrize('level',['VALIDATED_PATH','STATISTICAL_ASSOCIATION','CANDIDATE_RELATION','HYPOTHESIS'])
def test_relation_levels_without_evidence_degrade(real,level):
    s,contexts=real;r,_=request(s,contexts['D3']);r['claims'][0].update(claim_type='RELATION',relation_level=level)
    assert s.resolve_claims(r,'owner')['claims'][0]['validation_status']=='INSUFFICIENT_EVIDENCE'

def test_cross_owner_denied(real):
    s,contexts=real;r,_=request(s,contexts['D3'])
    with pytest.raises(PermissionError):s.resolve_claims(r,'intruder')

def test_prediction_gate_and_audit_semantics(real):
    s,contexts=real
    for semantic in ('BACKEND_GATE','CONDITIONAL_PREDICTION_NOT_OBSERVATION','AUDIT_ONLY'):
        r,f=request(s,contexts['D511'],semantic)
        out=s.resolve_claims(r,'owner');assert out['claims'][0]['facts'][0]['semantic']==semantic
        assert out['optimization_allowed'] is False

def test_waiting_cannot_support_fact(real):
    s,contexts=real;c=next(c for c in s.catalog() if c['chain']=='D511')
    ctx=s.create(dict(selection_id=c['selection_id'],as_of=5399,window=1800),'owner')
    r,f=request(s,ctx,'REFUSAL_REASON')
    with pytest.raises(ValueError):s.resolve_claims(r,'owner')
    r['claims'][0]['claim_type']='INSUFFICIENT_EVIDENCE'
    assert s.resolve_claims(r,'owner')['claims'][0]['validation_status']=='INSUFFICIENT_EVIDENCE'

def test_numeric_comparison_backend_only(real):
    s,contexts=real;ctx=contexts['D511'];cat=s.fact_catalog(ctx['context_id'],'owner')
    a=next(f for f in cat['facts'] if f['method']=='prediction.action' and f['semantic']=='CONDITIONAL_PREDICTION_NOT_OBSERVATION')
    b=next(f for f in cat['facts'] if f['method']=='prediction.delta' and f['dimensions']==a['dimensions'] and f['semantic']==a['semantic'])
    r,_=request(s,ctx,'BACKEND_GATE');r['claims'][0].update(claim_type='COMPARISON',comparison_basis='DIFFERENCE',
        evidence_refs=[{k:f[k] for k in ('fact_id','evidence_id','payload_sha256')} for f in (a,b)])
    assert s.resolve_claims(r,'owner')['claims'][0]['difference']==a['value']-b['value']

def test_http_favicon_facts_claims(real):
    import http.cookiejar,urllib.request,urllib.error,threading
    from causalverse.evidence_s1.gateway import make_server
    s,_=real;server=make_server(s,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    base='http://127.0.0.1:'+str(server.server_port)
    def get(route):return client.open(base+route,timeout=30)
    try:
        assert get('/favicon.ico').status==get('/favicon.svg').status==200
        csrf=json.load(get('/api/session'))['csrf'];case=json.load(get('/api/catalog'))[0]
        def post(route,value):return client.open(urllib.request.Request(base+route,data=json.dumps(value).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':csrf}),timeout=30)
        ctx=json.load(post('/api/contexts',dict(selection_id=case['selection_id'],as_of=5400,window=1800)))
        cat=json.load(get('/api/facts/'+ctx['context_id']));f=cat['facts'][0]
        request=dict(schema_version=cat['schema_version'],context_id=cat['context_id'],snapshot_sha256=cat['snapshot_sha256'],claims=[dict(claim_id='http1',claim_type='FACT' if f['evidence_status']=='INFERRED' else 'INSUFFICIENT_EVIDENCE',evidence_refs=[{k:f[k] for k in ('fact_id','evidence_id','payload_sha256')}])])
        result=json.load(post('/api/claims/resolve',request));assert result['claims'][0]['facts'][0]['value']==f['value']
        request['claims'][0]['value']=80
        with pytest.raises(urllib.error.HTTPError) as err:post('/api/claims/resolve',request)
        assert err.value.code==400
        assert json.load(get('/api/contracts'))['claim_schema']['properties']['schema_version']['const']=='s1.1-claims-1'
    finally:server.shutdown();server.server_close();thread.join()
