"""P0-04: all 480 conditions, actual ensemble/support calls, no future truth or fit."""
from contextlib import contextmanager
from dataclasses import replace
import copy
import json
import os
from pathlib import Path
import sys
import numpy as np
import pytest
from causalverse.decision.intervention_model import ConditionalPredictor,Ridge,history_features
from causalverse.decision.action_support import ActionSupport,candidate_disagreement
import causalverse.decision.intervention_calibration as original_calibration
import causalverse.decision.uncertainty as uncertainty
from causalverse.ai_runtime.registry import Registry
from causalverse.ai_runtime.contracts import AdmissionError
from causalverse.ai_runtime.prediction_runtime import PredictionRuntime,validate_prediction_contract,HORIZONS
from causalverse.ai_runtime.support_runtime import restore_members
from causalverse.ai_runtime.provenance import canonical

REG=Registry()
LOG=REG.trusted_json('artifacts/d5_1_1/data_log.json')['runs']
REFS=sorted(Path(r['folder']).name for r in LOG if r['split']=='test' and r['delta']==0)
assert len(REFS)==80

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(canonical(value),f,ensure_ascii=False,indent=2,allow_nan=False)


@contextmanager
def guarded(mp):
    audit={'forbidden_calls':[],'calls':{},'hooks':['fit','fit_transform','calibrate','conformal_radius','set_control','inject_fault','TEP']}
    def deny(*a,**kw):
        audit['forbidden_calls'].append('blocked entry');raise AssertionError('FORBIDDEN_CALL')
    for owner,name in [(ConditionalPredictor,'fit'),(Ridge,'fit'),(ActionSupport,'fit'),
                       (original_calibration,'calibrate'),(uncertainty,'conformal_radius')]:mp.setattr(owner,name,deny)
    for owner,name in [(ConditionalPredictor,'predict'),(Ridge,'predict'),(ActionSupport,'check')]:
        original=getattr(owner,name);label=owner.__name__+'.'+name
        def counted(*a,_original=original,_label=label,**kw):
            audit['calls'][_label]=audit['calls'].get(_label,0)+1
            return _original(*a,**kw)
        mp.setattr(owner,name,counted)
    def profile(frame,event,arg):
        if event!='call':return
        name=frame.f_code.co_name;path=frame.f_code.co_filename.replace('\\','/')
        if name in ('fit','fit_transform','calibrate','conformal_radius','set_control','inject_fault') or '/src/tep/' in path or '/causalverse/simulation/' in path:
            audit['forbidden_calls'].append({'name':name,'path':path});raise AssertionError('FORBIDDEN_CALL')
    old=sys.getprofile()
    try:
        sys.setprofile(profile);yield audit
    finally:sys.setprofile(old)


@pytest.fixture(scope='module')
def harness(tmp_path_factory):
    out=Path(os.environ['CAUSALVERSE_P004_EVIDENCE']) if 'CAUSALVERSE_P004_EVIDENCE' in os.environ else tmp_path_factory.mktemp('prediction')
    mp=pytest.MonkeyPatch()
    try:
        with guarded(mp) as audit:
            runtime=PredictionRuntime(out/'replay')
            yield runtime,audit,out
    finally:mp.undo()


@pytest.mark.parametrize('ref',REFS)
@pytest.mark.parametrize('kind',['action','delta'])
def test_all_conditions_and_masked_independence(ref,kind,harness,monkeypatch):
    runtime,audit,out=harness;key=kind+'_'+ref
    before=dict(audit['calls'])
    result=runtime.predict('D511:'+ref,kind=kind,request_id=key)
    assert result['status']=='INFERRED',result['reason']
    comparison=runtime.compare_archive(result);save(out/'comparisons'/(key+'.json'),comparison)
    original_bytes=runtime.registry.trusted_bytes;attempts=[]
    def mask(path):
        if path.startswith(('artifacts/d5_1_1/intervals_','artifacts/d5_1_1/predictions_')) or path in (
            'artifacts/d5_1_1/candidate_disagreement.json','artifacts/d5_1_1/support_results.json'):
            attempts.append(path);raise AdmissionError('FILE_MISSING','temporary prediction archive mapping disabled')
        return original_bytes(path)
    original_array=np.lib.npyio.NpzFile.__getitem__;keys=[]
    def no_future(self,key):
        keys.append(key)
        assert key not in ('truth','values','delta_values','rng_state','valve_position','future_truth','y'),key
        value=original_array(self,key)
        if key in ('t_seconds','XMEAS','XMV','command_before'):value=value[:5401]
        return value
    with monkeypatch.context() as mp:
        mp.setattr(runtime.registry,'trusted_bytes',mask)
        mp.setattr(np.lib.npyio.NpzFile,'__getitem__',no_future)
        isolated=runtime.predict('D511:'+ref,kind=kind,request_id=key+'-masked')
        assert isolated['status']=='INFERRED',isolated['reason']
        assert attempts==[], 'prediction must not read saved outputs'
        unavailable=runtime.compare_archive(isolated)
    save(out/'masked_comparisons'/(key+'.json'),unavailable)
    calls={k:v-before.get(k,0) for k,v in audit['calls'].items()}
    save(out/'guards'/(key+'.json'),{'calls':calls,'forbidden_calls':list(audit['forbidden_calls']),
        'inference_id':result['inference_id'],'masked_inference_id':isolated['inference_id'],
        'masked_future_keys_accessed':keys,'archive_attempts_after_comparison':attempts,
        'future_observation_arrays_limited_through':5400})
    assert comparison['status']=='MATCHED',comparison
    assert len(comparison['rows'])==3
    assert unavailable['status']=='UNAVAILABLE'
    for name in result['arrays']:assert np.array_equal(result['arrays'][name],isolated['arrays'][name]),name
    assert result['arrays']['members'].shape==(3,20,6,3)
    assert result['arrays']['candidate_members'].shape==(3,4,20,6,3)
    assert np.array_equal(result['arrays']['mean'],result['arrays']['members'].mean(1))
    assert all(r['contract_valid'] and not r['optimization_allowed'] for r in result['records'])
    assert all(r['uncertainty_status']=='INTERVAL_TOO_WIDE' for r in result['records'])
    assert all(r['candidate_audit_status']=='AUDIT_ONLY' for r in result['records'])
    assert calls['ConditionalPredictor.predict']==600 and calls['ActionSupport.check']==36
    assert not audit['forbidden_calls']


@pytest.fixture(scope='module')
def context(harness):return harness[0].reader.read('D511:test_631000_m14_a0','D511',as_of=5400)


@pytest.mark.parametrize('damage,code',[('member','MEMBER_PARAMETER_MISSING'),('shape','PARAMETER_SHAPE_ERROR'),('nan','NONFINITE_PARAMETER')])
@pytest.mark.parametrize('kind',['action','delta'])
def test_damaged_temporary_parameters(damage,code,kind,harness,tmp_path):
    parameters=dict(harness[0].parameters[kind]);key='19_model_coef'
    if damage=='member':del parameters[key]
    if damage=='shape':parameters[key]=parameters[key][:-1].copy()
    if damage=='nan':parameters[key]=parameters[key].copy();parameters[key][0,0]=np.nan
    with pytest.raises(AdmissionError,match=code) as error:restore_members(parameters,kind)
    save(tmp_path/'rejection.json',dict(damage=damage,kind=kind,reason=str(error.value),formal_files_modified=False))


@pytest.mark.parametrize('damage,code',[('delta','ACTION_UNSUPPORTED'),('duration','ACTION_UNSUPPORTED'),
    ('origin','ACTION_UNSUPPORTED'),('horizon','ACTION_UNSUPPORTED'),('command','COMMAND_SATURATION'),('missing_command','COMMAND_MISSING')])
def test_invalid_contracts(damage,code,context,harness,tmp_path):
    c=context;actions=(0,1,5);duration=120;origin=5400;horizons=HORIZONS
    if damage=='delta':actions=(2,)
    if damage=='duration':duration=121
    if damage=='origin':origin=5390
    if damage=='horizon':horizons=(10,30)
    if damage=='command':c=replace(c,command_before=101.)
    if damage=='missing_command':c=replace(c,command_before=None)
    with pytest.raises(AdmissionError,match=code) as error:
        validate_prediction_contract(c,harness[0].registry.entry('d511.action'),actions,duration,origin,horizons)
    save(tmp_path/'rejection.json',dict(damage=damage,reason=str(error.value)))


def test_complete_history_support_and_member_disagreement(context,harness,tmp_path):
    runtime=harness[0];h=context.values.copy();h[0,0]+=1e6
    members=np.array([m.predict(h,1,context.command_before) for m in runtime.models['action']])
    audit=runtime.support.evaluate(h,1,context.command_before,'action',members)
    assert 'history_or_command_outside_support' in audit['reasons']
    members=np.zeros((20,6,3));members[0]=100
    second=runtime.support.evaluate(context.values,1,context.command_before,'action',members)
    assert second['member_disagreement']>1 and 'ensemble_disagreement' in second['reasons']
    save(tmp_path/'negative_support.json',{'early_history_reasons':audit['reasons'],'member_disagreement':second['member_disagreement'],'member_reasons':second['reasons']})


def test_candidate_disagreement_preserves_rejection(context,harness,tmp_path):
    runtime=harness[0];pred=np.array([m.predict(context.values,1,context.command_before) for m in runtime.models['action']])
    audit=runtime.support.evaluate(context.values,1,context.command_before,'action',pred)
    expected=candidate_disagreement(audit['candidate_means'],np.array([.25,.5,5.]))
    assert audit['candidate_normalized_range']==expected
    assert audit['candidate_members'].shape==(4,20,6,3) and audit['candidate_audit_status']=='AUDIT_ONLY'
    assert expected>1 and 'candidate_mechanism_disagreement' in audit['reasons']
    save(tmp_path/'candidate_audit.json',{'range':expected,'status':audit['candidate_audit_status'],'reasons':audit['reasons']})


def test_delta_base_independence(context,harness,tmp_path,monkeypatch):
    runtime=harness[0];models=runtime.models['delta'];base_ids={id(m.base) for m in models};calls=[]
    original=Ridge.predict
    def capture(self,x):calls.append(id(self));return original(self,x)
    with monkeypatch.context() as mp:
        mp.setattr(Ridge,'predict',capture)
        actual=np.array([m.predict(context.values,0,context.command_before) for m in models])
    expected=np.array([original(m.base,history_features(context.values)[None,:]).reshape(6,3)+context.values[-1,:3] for m in models])
    assert len(calls)==20 and set(calls)==base_ids and np.array_equal(actual,expected)
    with (tmp_path/'delta_base.npz').open('xb') as f:np.savez_compressed(f,actual=actual,independent_base=expected)
    save(tmp_path/'base_proof.json',{'base_calls':len(calls),'distinct_base_members':len(set(calls)),
         'action_delta_regressor_calls':sum(i not in base_ids for i in calls),'future_truth_reads':0,'exactly_equal':True})


@pytest.mark.parametrize('kind',['action','delta'])
def test_joint_calibration_is_original_and_action_invariant(kind,harness,tmp_path):
    cal=harness[0].calibration;p=cal.load(kind);widths=[]
    for action in (0,1,5):
        bounds=cal.bounds(np.zeros((6,3)),kind,action);widths.append(bounds['full_width'])
        assert bounds['joint']==p['joint']
        assert np.array_equal(bounds['upper'],np.broadcast_to(p['joint']*cal.scales,(6,3)))
    assert np.array_equal(widths[0],widths[1]) and np.array_equal(widths[1],widths[2])
    save(tmp_path/'joint_calibration.json',dict(joint=p['joint'],width=widths[0].tolist(),
         sha256=harness[0].registry.entry('d511.calibration_'+kind)['parameter_sha256']))


def test_early_clock_and_invalid_delta_are_persisted(harness):
    runtime=harness[0]
    a=runtime.predict('D511:test_631000_m14_a0',kind='action',as_of=5399,request_id='early')
    b=runtime.predict('D511:test_631000_m14_a0',kind='delta',actions=(2,),request_id='bad-action')
    assert a['status']=='WAITING' and not a['contract_valid']
    assert b['status']=='REJECTED' and not b['contract_valid']
    assert not a['optimization_allowed'] and not b['optimization_allowed']
    assert 'causalverse.simulation' not in sys.modules
