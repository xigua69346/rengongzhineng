"""P0-02: 80-run replay, no-training/no-archive proof, temporal and hash isolation."""
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
import pytest
from causalverse.ai_runtime.contracts import AdmissionError
from causalverse.ai_runtime.detection_runtime import DetectionRuntime, NUMERIC_KEYS, ALARM_KEYS, observation_payload_hash
from causalverse.ai_runtime.provenance import canonical
from causalverse.ai_runtime.registry import Registry
from causalverse.data.preprocessing import Standardizer
from causalverse.detection.pca import PCADetector
from causalverse.detection.threshold import ThresholdDetector
import causalverse.detection.statistics as statistics

REGISTRY = Registry()
TEST_RUNS = [r['dataset_run_id'] for r in REGISTRY.trusted_json('artifacts/d3/dataset/split_plan.json')['runs'] if r['split']=='test']
assert len(TEST_RUNS)==80


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(canonical(value),f,ensure_ascii=False,indent=2,allow_nan=False)


@pytest.fixture(scope='module')
def evidence(tmp_path_factory):
    return Path(os.environ['CAUSALVERSE_P002_EVIDENCE']) if 'CAUSALVERSE_P002_EVIDENCE' in os.environ else tmp_path_factory.mktemp('detection')


@contextmanager
def blocked_training(monkeypatch):
    audit={'installed':['Standardizer.fit','PCADetector.fit','ThresholdDetector.fit','statistics.control_limit',
                        'profile:fit/fit_transform/calibrate/control_limit/simulation/TEP'],
           'forbidden_calls':[], 'algorithm_calls':{}}
    def forbidden(*args,**kwargs):
        audit['forbidden_calls'].append('patched training/control-limit entry')
        raise AssertionError('FORBIDDEN_TRAINING_OR_CONTROL_LIMIT_ESTIMATION')
    for owner,name in [(Standardizer,'fit'),(PCADetector,'fit'),(ThresholdDetector,'fit'),(statistics,'control_limit')]:
        monkeypatch.setattr(owner,name,forbidden)
    for owner,name in [(Standardizer,'transform'),(PCADetector,'scores'),(ThresholdDetector,'score'),(ThresholdDetector,'contributions')]:
        original=getattr(owner,name);label=owner.__name__+'.'+name
        def counted(*args,_original=original,_label=label,**kwargs):
            audit['algorithm_calls'][_label]=audit['algorithm_calls'].get(_label,0)+1
            return _original(*args,**kwargs)
        monkeypatch.setattr(owner,name,counted)
    def profile(frame,event,arg):
        if event!='call':return
        filename=frame.f_code.co_filename.replace('\\','/')
        name=frame.f_code.co_name
        if name in ('fit','fit_transform','calibrate','control_limit','set_control','inject_fault') or '/causalverse/simulation/' in filename or '/src/tep/' in filename:
            audit['forbidden_calls'].append({'name':name,'file':filename})
            raise AssertionError('FORBIDDEN_CALL')
    previous=sys.getprofile()
    try:
        sys.setprofile(profile)
        yield audit
    finally:sys.setprofile(previous)


@pytest.mark.parametrize('run',TEST_RUNS)
def test_full_replay_and_archive_independence(run,evidence,monkeypatch):
    runtime=DetectionRuntime(evidence/'replay'/run)
    with blocked_training(monkeypatch) as audit:
        result=runtime.detect('D3:'+run,as_of=14399,request_id='replay-'+run)
        assert result['status']=='INFERRED',result['reason']
        comparison=runtime.compare_archive(result)
        save(evidence/'comparisons'/(run+'.json'),comparison)
        original=runtime.registry.trusted_bytes
        attempted=[]
        def hide_outputs(relative):
            if relative.startswith('artifacts/d3/detection/test_'):
                attempted.append(relative)
                raise AdmissionError('FILE_MISSING','temporary archive mapping disabled')
            return original(relative)
        monkeypatch.setattr(runtime.registry,'trusted_bytes',hide_outputs)
        isolated=runtime.detect('D3:'+run,as_of=14399,request_id='archive-masked-'+run)
        assert isolated['status']=='INFERRED',isolated['reason']
        assert attempted==[], 'detect must never try to open archive outputs'
        missing=runtime.compare_archive(isolated)
        save(evidence/'masked_comparisons'/(run+'.json'),missing)
        save(evidence/'guards'/(run+'.json'),dict(audit,archive_read_attempts=attempted,
                                                full_inference_id=result['inference_id'],masked_inference_id=isolated['inference_id']))
    assert comparison['status']=='MATCHED',comparison
    assert result['sample_count']==70 and result['retained_components']==29
    assert np.array_equal(result['arrays']['observation_time'],np.arange(1800,14400,180))
    assert result['arrays']['projection'].shape==(70,29)
    assert all(result['arrays'][k].shape==(70,41) for k in ('T2_contribution','SPE_contribution','threshold_contribution'))
    assert all(result['arrays'][k].dtype==bool for k in ALARM_KEYS)
    assert missing['status']=='UNAVAILABLE'
    for key in NUMERIC_KEYS+ALARM_KEYS+('observation_time',):
        assert np.array_equal(result['arrays'][key],isolated['arrays'][key]),key
    assert isolated['observation_payload_hash']==result['observation_payload_hash']
    assert isolated['inference_identity_hash']==result['inference_identity_hash']
    assert isolated['inference_id']!=result['inference_id']
    assert audit['forbidden_calls']==[]
    assert audit['algorithm_calls']=={'Standardizer.transform':2,'PCADetector.scores':2,
                                      'ThresholdDetector.score':2,'ThresholdDetector.contributions':4}


@pytest.mark.parametrize('clock,count',[(1799,0),(1800,1),(1979,1),(1980,2),(2160,3)])
def test_clock_boundaries(clock,count,tmp_path):
    result=DetectionRuntime(tmp_path).detect('D3:test_f14_00',as_of=clock,request_id='clock')
    assert result['status']==('INFERRED' if count else 'WAITING')
    assert len(result['arrays'].get('observation_time',[]))==count
    if count:assert max(result['arrays']['observation_time'])<=clock
    else:assert 'WINDOW_INCOMPLETE' in result['reason']


def test_future_file_changes_leave_numeric_hash_and_scores_unchanged(tmp_path):
    """Public-array-only temporary trajectory; trusted test mapping updates hashes explicitly."""
    reg=Registry();ref='D3:test_f14_00'
    raw='artifacts/d3/dataset/raw/test_f14_00/trajectory.npz'
    manifest_path='artifacts/d3/dataset/raw/test_f14_00/manifest.json'
    public=reg.trusted_npz(raw,('t_seconds','XMEAS','XMV'))
    manifests=reg.trusted_json(manifest_path)
    original_path=reg.path
    def overlay(relative):
        candidate=tmp_path/'mapping'/relative
        return candidate if candidate.is_file() else original_path(relative)
    reg.path=overlay
    def write_mapping():
        p=tmp_path/'mapping'/raw;p.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(p,**public)
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        reg.baseline[raw]=dict(reg.baseline[raw],sha256=sha)
        manifests['sha256']['trajectory.npz']=sha
        p=tmp_path/'mapping'/manifest_path
        p.write_text(json.dumps(manifests),encoding='utf-8')
        reg.baseline[manifest_path]=dict(reg.baseline[manifest_path],sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    write_mapping()
    a=DetectionRuntime(tmp_path/'before',reg).detect(ref,as_of=1980,request_id='future-before')
    public['XMEAS'][public['t_seconds']>1980]+=12345
    public['XMV'][public['t_seconds']>1980]=99
    write_mapping()
    b=DetectionRuntime(tmp_path/'after',reg).detect(ref,as_of=1980,request_id='future-after')
    assert a['status']==b['status']=='INFERRED'
    assert a['source_file_hash']!=b['source_file_hash']
    assert a['inference_identity_hash']!=b['inference_identity_hash']
    assert a['observation_payload_hash']==b['observation_payload_hash']
    for key in a['arrays']:assert np.array_equal(a['arrays'][key],b['arrays'][key])
    save(tmp_path/'future_proof.json',{'before':{k:a[k] for k in ('source_file_hash','observation_payload_hash','inference_identity_hash')},
                                       'after':{k:b[k] for k in ('source_file_hash','observation_payload_hash','inference_identity_hash')},
                                       'all_scores_and_alarms_exactly_equal':True})


def test_same_observations_different_as_of_hashes(tmp_path):
    runtime=DetectionRuntime(tmp_path)
    a=runtime.detect('D3:test_f14_00',as_of=1800,request_id='one')
    b=runtime.detect('D3:test_f14_00',as_of=1979,request_id='two')
    assert a['status']==b['status']=='INFERRED'
    assert a['observation_payload_hash']==b['observation_payload_hash']
    assert a['inference_identity_hash']!=b['inference_identity_hash']


@pytest.mark.parametrize('ref',['../secret','D511:test_631000_m14_a1','D3:unknown'])
def test_rejected_inputs_leave_trace(ref,tmp_path):
    result=DetectionRuntime(tmp_path).detect(ref,as_of=5400,request_id='bad')
    assert result['status']=='REJECTED' and result['reason']
    assert not result['arrays']
    assert (tmp_path/result['inference_id']/'result.json').is_file()


@pytest.mark.parametrize('which',['equal','t2_only','spe_only'])
def test_strict_greater_and_or(which,tmp_path,monkeypatch):
    limits=REGISTRY.trusted_json('artifacts/d3/detection/model_manifest.json')['limits']
    def controlled(self,z):
        n=len(z)
        return dict(T2=np.full(n,limits['T2']*(1.01 if which=='t2_only' else 1)),
                    SPE=np.full(n,limits['SPE']*(1.01 if which=='spe_only' else 1)),
                    projection=np.zeros((n,29)),T2_contribution=np.zeros((n,41)),SPE_contribution=np.zeros((n,41)))
    monkeypatch.setattr(PCADetector,'scores',controlled)
    monkeypatch.setattr(ThresholdDetector,'score',lambda self,z:np.full(len(z),limits['Threshold']))
    result=DetectionRuntime(tmp_path).detect('D3:test_f14_00',as_of=1980,request_id='boundary')
    assert result['status']=='INFERRED'
    assert np.all(result['arrays']['pred_PCA']==(which!='equal'))
    assert not result['arrays']['pred_Threshold'].any()


def test_no_label_or_hidden_array_access(tmp_path,monkeypatch):
    keys=[];original=np.lib.npyio.NpzFile.__getitem__
    forbidden={'y','rng_state','valve_position','future_truth','truth','delta_values'}
    def read(self,key):
        keys.append(key)
        assert key not in forbidden,key
        return original(self,key)
    monkeypatch.setattr(np.lib.npyio.NpzFile,'__getitem__',read)
    runtime=DetectionRuntime(tmp_path)
    result=runtime.detect('D3:test_f14_00',as_of=1980,request_id='keys')
    assert result['status']=='INFERRED'
    assert runtime.compare_archive(result)['status']=='MATCHED'
    save(tmp_path/'keys.json',{'requested_keys':keys,'forbidden_keys_requested':sorted(set(keys)&forbidden)})


def test_mismatch_is_reported_without_changing_computed_result(tmp_path,monkeypatch):
    runtime=DetectionRuntime(tmp_path)
    result=runtime.detect('D3:test_f14_00',as_of=1980,request_id='mismatch')
    original=runtime.registry.trusted_npz
    def wrong_reference(path,keys):
        a=original(path,keys)
        if path=='artifacts/d3/detection/test_f14_00.npz':a['T2'][0]+=1
        return a
    monkeypatch.setattr(runtime.registry,'trusted_npz',wrong_reference)
    before=result['arrays']['T2'].copy()
    comparison=runtime.compare_archive(result)
    save(tmp_path/'intentional_mismatch.json',comparison)
    assert comparison['status']=='MISMATCH'
    assert comparison['metrics']['T2']['mismatches'][0]['observation_time']==1800
    assert np.array_equal(before,result['arrays']['T2'])
