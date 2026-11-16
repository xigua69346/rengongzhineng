"""S1 integration acceptance: real frozen inference, no mock numerical output."""
import http.cookiejar
import json
import os
from pathlib import Path
import sys
import threading
import urllib.request
import urllib.error
import numpy as np
import pytest
from causalverse.evidence_s1.service import EvidenceService, digest
from causalverse.evidence_s1.gateway import make_server
from causalverse.ai_runtime.observation_reader import ObservationReader
from causalverse.ai_runtime.contracts import AdmissionError

ROOT = Path(os.environ['S1_ACCEPTANCE'])

@pytest.fixture(scope='module')
def setup():
    s = EvidenceService(ROOT / 'test_runtime')
    calls = []
    forbidden = []
    def profile(frame, event, arg):
        if event == 'call':
            name = frame.f_code.co_name
            if name in ('fit', 'fit_transform', 'calibrate', 'minimize', 'set_control', 'inject_fault'):
                forbidden.append(name)
                raise AssertionError('FORBIDDEN_CALL:' + name)
            if name in ('detect', 'diagnose', 'predict') and 'ai_runtime' in frame.f_code.co_filename:
                calls.append(name)
    sys.setprofile(profile)
    contexts = {}
    try:
        for chain in ('D3', 'D511'):
            case = next(c for c in s.catalog() if c['chain'] == chain)
            contexts[chain] = s.create(dict(selection_id=case['selection_id'], as_of=5400, window=1800), 'alice')
    finally:
        sys.setprofile(None)
    (ROOT / 'actual_calls.json').write_text(json.dumps(dict(calls=calls, forbidden=forbidden)), encoding='utf-8')
    return s, contexts, calls, forbidden

def test_real_three_runtime_calls(setup):
    s, ctx, calls, forbidden = setup
    assert calls.count('detect') == 1 and calls.count('diagnose') == 6 and calls.count('predict') == 2
    assert forbidden == []
    assert all(e['status'] == 'INFERRED' for e in ctx['D3']['evidence'][:4])
    assert all(e['status'] == 'INFERRED' for e in ctx['D511']['evidence'][1:])

@pytest.mark.parametrize('kind', ['prediction.action', 'prediction.delta'])
def test_prediction_members_intervals_original_audits(setup, kind):
    e = next(e for e in setup[1]['D511']['evidence'] if e['kind'] == kind)
    d = e['data']
    assert np.array(d['arrays']['members']).shape == (3,20,6,3)
    assert np.array(d['arrays']['candidate_members']).shape == (3,4,20,6,3)
    assert d['historical_comparison']['status'] == 'MATCHED'
    assert d['original_audit_matches_recomputation'] is True
    assert len(d['original_audit']) == 3
    assert all(r['uncertainty_status'] == 'INTERVAL_TOO_WIDE' and r['optimization_allowed'] is False for r in d['records'])

def test_public_no_private_identity_or_hidden_fields(setup):
    s, contexts, _, _ = setup
    for ctx in contexts.values():
        text = json.dumps(ctx)
        private = s.index[ctx['context_id']]
        for secret in (private['data_ref'], private['identity']['run_id'], private['trajectory']):
            assert secret not in text
        for token in ('future_truth', 'rng_state', 'fault_id', 'valve_position', 'artifacts/', 'parent_run_id', 'snapshot_id'):
            assert token not in text

def test_identity_sha_and_numerical_provenance(setup):
    s, contexts, _, _ = setup
    for ctx in contexts.values():
        mapping = s.index[ctx['context_id']]
        assert s.registry.baseline[mapping['trajectory']]['sha256'] == digest(s.registry.root / mapping['trajectory'])
        for source in mapping['sources']:
            if 'inference_id' in source:
                assert source['evidence_id'] in [e['evidence_id'] for e in ctx['evidence']]
                if source.get('observation_payload_hash'):
                    assert len(source['observation_payload_hash']) == 64

@pytest.mark.parametrize('chain,time', [('D3',3779), ('D511',5399)])
def test_waiting_exact_window_boundary(setup, chain, time):
    s = setup[0]
    c = next(c for c in s.catalog() if c['chain'] == chain)
    ctx = s.create(dict(selection_id=c['selection_id'], as_of=time, window=180), 'waiting')
    if chain == 'D3':
        assert all(e['status'] == 'WAITING' for e in ctx['evidence'] if e['kind'].startswith('diagnosis.'))
    else:
        assert all(e['status'] == 'WAITING' for e in ctx['evidence'] if e['kind'].startswith('prediction.'))

def test_future_values_cannot_change_fixed_window_or_prediction(setup, monkeypatch):
    s, contexts, _, _ = setup
    original = ObservationReader._raw
    def changed(reader, path):
        t, x, u = original(reader, path)
        x, u = x.copy(), u.copy()
        x[t > 5400] += 10000
        u[t > 5400] += 5000
        return t, x, u
    monkeypatch.setattr(ObservationReader, '_raw', changed)
    c = next(c for c in s.catalog() if c['alias'] == contexts['D511']['alias'])
    newer = s.create(dict(selection_id=c['selection_id'], as_of=5400, window=1800), 'future-test')
    for before, after in zip(contexts['D511']['evidence'][1:], newer['evidence'][1:]):
        assert after['status'] == 'INFERRED'
        if before['kind'].startswith('diagnosis.'):
            assert before['data']['records'] == after['data']['records']
        else:
            assert before['data']['arrays'] == after['data']['arrays']

def test_observed_time_never_after_asof(setup):
    for ctx in setup[1].values():
        for e in ctx['evidence']:
            d = e['data']
            times = d.get('observation_time', []) + d.get('arrays', {}).get('observation_time', [])
            for row in d.get('records', []):
                times += row.get('observation_time', [])
            assert all(t <= ctx['as_of'] for t in times)

def test_chains_not_paired(setup):
    assert setup[1]['D3']['evidence'][-1]['status'] == 'UNAVAILABLE'
    assert setup[1]['D511']['evidence'][0]['status'] == 'UNAVAILABLE'
    with pytest.raises(AdmissionError):
        setup[0].detection.reader.read(setup[0].index[setup[1]['D3']['context_id']]['data_ref'], 'D511', as_of=5400)

@pytest.mark.parametrize('change', [dict(as_of=-1),dict(as_of=True),dict(as_of=99999),dict(window=181),dict(selection_id='../raw'),dict(path='raw.npz'),dict(future_truth=[1]),dict(api_key='not-a-key')])
def test_invalid_inputs_rejected(setup, change):
    s = setup[0]
    request = dict(selection_id=s.catalog()[0]['selection_id'], as_of=5400, window=1800)
    request.update(change)
    with pytest.raises((ValueError, TypeError)):
        s.create(request, 'alice')

def test_immutable_copy_owner_and_cross_context_claim(setup):
    s, contexts, _, _ = setup
    ctx = contexts['D3']
    copy = s.get(ctx['context_id'], 'alice')
    copy['as_of'] = -1
    assert s.get(ctx['context_id'], 'alice')['as_of'] == 5400
    with pytest.raises(PermissionError):
        s.get(ctx['context_id'], 'mallory')
    e = ctx['evidence'][0]
    assert s.evidence(e['evidence_id'], 'alice') == e
    claim = dict(context_id=ctx['context_id'], evidence_id=e['evidence_id'], claim_type='COMPUTATION_AVAILABLE')
    assert s.validate_claim(claim, 'alice')
    claim['evidence_id'] = contexts['D511']['evidence'][1]['evidence_id']
    with pytest.raises(ValueError):
        s.validate_claim(claim, 'alice')

def test_snapshot_tamper_detected(setup):
    s = setup[0]
    c = s.catalog()[0]
    ctx = s.create(dict(selection_id=c['selection_id'], as_of=0, window=180), 'tamper')
    path = s.root / 'snapshots' / (ctx['context_id'] + '.json')
    path.write_text('{}', encoding='utf-8')  # Only this new disposable test snapshot.
    with pytest.raises(ValueError, match='SNAPSHOT_HASH_MISMATCH'):
        s.get(ctx['context_id'], 'tamper')

def test_hash_mismatch_rejected_without_modifying_original(setup, monkeypatch):
    s = setup[0]
    relative = s.index[setup[1]['D3']['context_id']]['trajectory']
    original = s.registry.baseline[relative]
    monkeypatch.setitem(s.registry.baseline, relative, dict(original, sha256='0'*64))
    with pytest.raises(AdmissionError):
        s.registry.trusted_npz(relative, ('XMEAS',))

def test_no_key_http_security_occupancy_and_console(setup, monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    s = setup[0]
    server = make_server(s, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def fetch(path, data=None, headers=None):
        return client.open(urllib.request.Request(base+path, data=data, headers=headers or {}), timeout=30)
    try:
        assert json.load(fetch('/api/health'))['llm_enabled'] is False
        assert b'CAUSALVERSE' in fetch('/').read()
        assert fetch('/app.js').headers['Content-Security-Policy'].find("connect-src 'self'") >= 0
        csrf = json.load(fetch('/api/session'))['csrf']
        assert len(json.load(fetch('/api/catalog'))) == 160
        with pytest.raises(urllib.error.HTTPError) as exc:
            fetch('/api/contexts', b'{}', {'Content-Type':'application/json'})
        assert exc.value.code == 403
        for path in ('/_private/cases.json','/../AI_PHASE3_P0_04_REPORT.md','/api/control'):
            with pytest.raises(urllib.error.HTTPError):
                fetch(path)
        with pytest.raises(urllib.error.HTTPError) as exc:
            fetch('/api/catalog', headers={'Origin':'https://evil.example'})
        assert exc.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as exc:
            fetch('/api/contexts/'+setup[1]['D3']['context_id'])
        assert exc.value.code == 403
        with pytest.raises(OSError):
            make_server(s, server.server_port)
        req=dict(selection_id=s.catalog()[0]['selection_id'],as_of=0,window=180)
        response=fetch('/api/contexts',json.dumps(req).encode(),{'Content-Type':'application/json','X-CSRF-Token':csrf})
        result=json.load(response)
        assert response.status == 201 and result['optimization_allowed'] is False
        assert json.load(fetch('/api/contexts/'+result['context_id'])) == result
    finally:
        server.shutdown();server.server_close();thread.join()
