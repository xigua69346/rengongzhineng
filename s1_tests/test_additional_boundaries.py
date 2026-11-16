"""Additional S1 boundary proofs; every result is recomputed by the existing runtimes."""
import json
import os
from pathlib import Path
import numpy as np
import pytest
from causalverse.evidence_s1.service import EvidenceService
from causalverse.ai_runtime.observation_reader import ObservationReader

@pytest.fixture(scope='module')
def service():
    return EvidenceService(Path(os.environ['S1_ACCEPTANCE']) / 'additional_runtime')

@pytest.mark.parametrize('window', [180,600,1800])
def test_completed_and_incomplete_windows(service, window):
    case=next(c for c in service.catalog() if c['chain']=='D3')
    results=[]
    for t in (3600+window-1,3600+window):
        ctx=service.create(dict(selection_id=case['selection_id'],as_of=t,window=window),'boundary')
        results.append([e['status'] for e in ctx['evidence'] if e['kind'].startswith('diagnosis.')])
    assert results == [['WAITING']*3,['INFERRED']*3]

def test_d3_future_values_do_not_change_detection(service, monkeypatch):
    case=next(c for c in service.catalog() if c['chain']=='D3')
    req=dict(selection_id=case['selection_id'],as_of=3600,window=180)
    first=service.create(req,'before')['evidence'][0]
    original=ObservationReader._raw
    def perturb(reader,path):
        t,x,u=original(reader,path);x=x.copy();u=u.copy()
        x[t>3600]+=10000;u[t>3600]+=10000
        return t,x,u
    monkeypatch.setattr(ObservationReader,'_raw',perturb)
    second=service.create(req,'after')['evidence'][0]
    assert first['status']==second['status']=='INFERRED'
    assert first['data']==second['data']

def test_no_hidden_npz_keys_or_external_network(service, monkeypatch):
    import socket
    original=service.registry.trusted_npz
    accessed=[]
    allowed={'t_seconds','XMEAS','XMV','values','history','command','command_before',
             'identifiers','horizons','targets','prediction','joint_lower','joint_upper','disagreement'}
    def checked(path,keys):
        accessed.extend(keys)
        assert set(keys)<=allowed
        return original(path,keys)
    monkeypatch.setattr(service.registry,'trusted_npz',checked)
    def denied(*args,**kwargs):
        raise AssertionError('NETWORK_NOT_ALLOWED_IN_EVIDENCE_COMPUTATION')
    monkeypatch.setattr(socket.socket,'connect',denied)
    case=next(c for c in service.catalog() if c['chain']=='D511')
    ctx=service.create(dict(selection_id=case['selection_id'],as_of=5400,window=1800),'key-test')
    assert all(e['status']=='INFERRED' for e in ctx['evidence'][1:])
    assert accessed
    (Path(os.environ['S1_ACCEPTANCE'])/'accessed_npz_keys.json').write_text(json.dumps(sorted(set(accessed))),encoding='utf8')
