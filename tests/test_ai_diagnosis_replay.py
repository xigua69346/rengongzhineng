"""P0-03 only: original models, all windows, raw external reconstruction and refusals."""
from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import numpy as np
import pytest
import scipy.optimize
import causalverse.decision.mechanism as mechanism
from causalverse.causal.dynamic import MechanismEvidence
from causalverse.ai_runtime.contracts import AdmissionError
from causalverse.ai_runtime.registry import Registry
from causalverse.ai_runtime.window_contract import WindowReader, validate_window
from causalverse.ai_runtime.diagnosis_runtime import DiagnosisRuntime, candidate_result, frozen_var
from causalverse.ai_runtime.provenance import canonical


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(canonical(obj),f,ensure_ascii=False,indent=2,allow_nan=False)


@pytest.fixture(scope='module')
def evidence(tmp_path_factory):
    return Path(os.environ['CAUSALVERSE_P003_EVIDENCE']) if 'CAUSALVERSE_P003_EVIDENCE' in os.environ else tmp_path_factory.mktemp('diagnosis')


@contextmanager
def guarded(monkeypatch):
    audit={'forbidden_calls':[],'algorithm_calls':{},'hooks':['fit','minimize','calibrate','simulation','TEP']}
    def deny(*a,**kw):
        audit['forbidden_calls'].append('patched forbidden entry')
        raise AssertionError('FORBIDDEN_TRAINING_CALIBRATION_OPTIMIZATION')
    for owner,name in [(mechanism.SmallVAR,'fit'),(mechanism.LogisticMechanism,'fit'),(mechanism.CandidatePolicy,'fit'),
                       (MechanismEvidence,'fit'),(MechanismEvidence,'calibrate'),(mechanism,'minimize'),(scipy.optimize,'minimize')]:
        monkeypatch.setattr(owner,name,deny)
    for owner,name in [(mechanism.SmallVAR,'residuals'),(mechanism.LogisticMechanism,'scores'),(MechanismEvidence,'distances')]:
        original=getattr(owner,name);label=owner.__name__+'.'+name
        def called(*a,_original=original,_label=label,**kw):
            audit['algorithm_calls'][_label]=audit['algorithm_calls'].get(_label,0)+1
            return _original(*a,**kw)
        monkeypatch.setattr(owner,name,called)
    def profile(frame,event,arg):
        if event!='call':return
        path=frame.f_code.co_filename.replace('\\','/');name=frame.f_code.co_name
        if name in ('fit','fit_transform','calibrate','minimize','set_control','inject_fault') or '/src/tep/' in path or '/causalverse/simulation/' in path:
            audit['forbidden_calls'].append({'name':name,'path':path});raise AssertionError('FORBIDDEN_CALL')
    old=sys.getprofile()
    try:
        sys.setprofile(profile);yield audit
    finally:sys.setprofile(old)


@pytest.mark.parametrize('split',['test','external'])
@pytest.mark.parametrize('window',[180,600,1800])
@pytest.mark.parametrize('kind',['static','VAR','logistic'])
def test_full_replay_and_masked_independence(split,window,kind,evidence,monkeypatch):
    key=f'{split}_{kind}_{window}'
    runtime=DiagnosisRuntime(evidence/'replay'/key)
    refs=['D3:'+r['dataset_run_id'] for r in runtime.windows.protocol['d3_runs'] if r['split']=='test'] if split=='test' else ['D511:'+n for n in runtime.windows.external]
    with guarded(monkeypatch) as audit:
        result=runtime.diagnose(refs,kind=kind,window=window,as_of=3600+window,request_id=key)
        assert result['status']=='INFERRED',result['reason']
        comparison=runtime.compare_archive(result)
        save(evidence/'comparisons'/(key+'.json'),comparison)
        original=runtime.registry.trusted_bytes;attempts=[]
        def blocked(path):
            if path=='artifacts/d5_1_2/diagnoses.json' or path.startswith('artifacts/d5_1_2/features_'):
                attempts.append(path);raise AdmissionError('FILE_MISSING','temporary archive mapping disabled')
            return original(path)
        monkeypatch.setattr(runtime.registry,'trusted_bytes',blocked)
        isolated=runtime.diagnose(refs,kind=kind,window=window,as_of=3600+window,request_id=key+'-masked')
        assert isolated['status']=='INFERRED',isolated['reason']
        assert attempts==[], 'features/diagnoses may not enter inference'
        unavailable=runtime.compare_archive(isolated)
        save(evidence/'masked_comparisons'/(key+'.json'),unavailable)
        save(evidence/'guards'/(key+'.json'),dict(audit,archive_attempts_after_comparison=attempts,
            inference_id=result['inference_id'],masked_inference_id=isolated['inference_id']))
    assert comparison['status']=='MATCHED',comparison
    assert len(comparison['records'])==len(result['records'])==80
    assert unavailable['status']=='UNAVAILABLE'
    assert audit['forbidden_calls']==[]
    for k in result['arrays']:assert np.array_equal(result['arrays'][k],isolated['arrays'][k]),k
    for row in result['records']:
        assert row['columns']==('T9','C21','P7','U10')
        assert row['observation_time']==tuple(range(3600,3600+window,10))
        assert row['refused']==(len(row['candidates'])!=1)
    assert not result['scores_are_calibrated_probabilities']
    assert result['selection_reference']['selected_windows']=={'static':1800,'VAR':1800,'logistic':1800}


@pytest.mark.parametrize('window',[180,600,1800])
def test_waiting_until_complete(window,tmp_path):
    runtime=DiagnosisRuntime(tmp_path)
    for ref in ['D3:test_f14_00','D511:test_631000_m14_a0']:
        r=runtime.diagnose([ref],kind='static',window=window,as_of=3600+window-1,request_id='early')
        assert r['status']=='WAITING' and not r['arrays']
        assert 'WINDOW_INCOMPLETE' in r['reason']


@pytest.mark.parametrize('origin',[0,3601,5400])
def test_illegal_origin(origin,tmp_path):
    r=DiagnosisRuntime(tmp_path).diagnose(['D3:test_f14_00'],kind='VAR',window=180,as_of=5400,origin=origin,request_id='bad-origin')
    assert r['status']=='REJECTED' and 'ORIGIN_UNSUPPORTED' in r['reason']


@pytest.mark.parametrize('damage,code',[('grid','TIME_GRID_ERROR'),('column','COLUMN_ORDER_ERROR'),
    ('missing','SHAPE_ERROR'),('units','UNIT_ERROR'),('future','FUTURE_INPUT')])
def test_invalid_observations(damage,code,tmp_path):
    w=WindowReader(Registry());c=w.read('D3:test_f14_00',window=180,as_of=3780)
    if damage=='grid':c=replace(c,observation_time=(3601,)+c.observation_time[1:])
    if damage=='column':c=replace(c,columns=c.columns[::-1])
    if damage=='missing':c=replace(c,values=c.values[:,:3])
    if damage=='units':c=replace(c,units=('Kelvin',)+c.units[1:])
    if damage=='future':c=replace(c,observation_time=c.observation_time[:-1]+(3790,))
    with pytest.raises(AdmissionError,match=code) as error:validate_window(c,w.contract)
    save(tmp_path/'rejection.json',{'damage':damage,'expected':code,'actual':str(error.value)})


def test_seven_node_var_refused(tmp_path):
    with pytest.raises(AdmissionError,match='CONTRACT_MISMATCH') as first:frozen_var(Registry(),'d4.var7')
    with pytest.raises(AdmissionError,match='CONTRACT_MISMATCH') as second:Registry().load('d4.var7','D512')
    save(tmp_path/'rejection.json',{'runtime_rejection':str(first.value),'registry_rejection':str(second.value)})


@pytest.mark.parametrize('scores,raw,candidates,refused,reason',[
    ([.7,.2,.08,.02],[False]*4,[],True,'empty_candidate_outside_known_signature'),
    ([.7,.2,.08,.02],[True,True,False,False],[0,4],True,'multiple_candidates'),
    ([.48,.46,.04,.02],[True,False,False,False],[0,4],True,'multiple_candidates'),
    ([.7,.2,.08,.02],[False,True,False,False],[0,4],True,'multiple_candidates'),
    ([.7,.2,.08,.02],[True,False,False,False],[0],False,'singleton')])
def test_candidate_edge_cases(scores,raw,candidates,refused,reason,tmp_path):
    _,_,records=candidate_result(np.array([scores]),np.array([raw]))
    record=records[0];save(tmp_path/'candidate_case.json',record)
    assert record['candidates']==candidates and record['refused']==refused and record['reason']==reason


@pytest.mark.parametrize('ref',['D511:test_631000_m14_a1','D511:train_611000_m14_a0','../secret'])
def test_external_scope_and_paths_rejected(ref,tmp_path):
    r=DiagnosisRuntime(tmp_path).diagnose([ref],kind='static',window=180,as_of=5400,request_id='bad-scope')
    assert r['status']=='REJECTED' and r['reason']


def test_no_hidden_or_label_array_access(tmp_path,monkeypatch):
    original=np.lib.npyio.NpzFile.__getitem__;keys=[]
    def getitem(self,key):
        keys.append(key)
        assert key not in ('y','truth','rng_state','valve_position','delta_values','test_y','external_y','train_y','validation_y'),key
        return original(self,key)
    monkeypatch.setattr(np.lib.npyio.NpzFile,'__getitem__',getitem)
    runtime=DiagnosisRuntime(tmp_path)
    for ref in ['D3:test_f14_00','D511:test_631000_m14_a0']:
        r=runtime.diagnose([ref],kind='logistic',window=180,as_of=3780,request_id='keys')
        assert r['status']=='INFERRED'
        assert runtime.compare_archive(r)['status']=='MATCHED'
    save(tmp_path/'keys.json',{'requested_keys':keys})
