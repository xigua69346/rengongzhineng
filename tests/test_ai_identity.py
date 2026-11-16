from dataclasses import replace
import json
import sys
import numpy as np
import pytest
from causalverse.ai_runtime.registry import Registry
from causalverse.ai_runtime.identity import DataIdentity, same_identity
from causalverse.ai_runtime.observation_reader import ObservationReader
from causalverse.ai_runtime.contracts import (AdmissionError, InferenceRequest, EvaluationContext,
                                             validate_observations)
from causalverse.ai_runtime.provenance import stable_hash, trace_admission


@pytest.fixture(scope='module')
def reader(): return ObservationReader(Registry())


@pytest.mark.parametrize('task,as_of,window,shape', [('D3',1980,None,(2,41)),
    ('D4',100,None,(11,7)),('D512',3780,180,(18,4)),
    ('D512',4200,600,(60,4)),('D512',5400,1800,(180,4)),('D511',5400,None,(6,7))])
def test_legal_contracts(reader, task, as_of, window, shape):
    ref = 'D511:test_631000_m14_a1' if task=='D511' else 'D3:test_f14_00'
    c = reader.read(ref,task,as_of=as_of,window=window)
    assert c.values.shape==shape
    assert max(c.observation_time)<=as_of
    assert not c.values.flags.writeable
    if task=='D511':
        assert c.command_before == 44.98640640212553
        assert c.command_before != c.values[-1,5]


@pytest.mark.parametrize('field,value', [('run_id','other'),('split','train'),
    ('parent_run_id','other'),('snapshot_id','other'),('branch_id','other'),('dataset_id','D3')])
def test_identity_mismatch(field,value):
    a=DataIdentity('D511','run','test','branch','parent','snapshot')
    with pytest.raises(AdmissionError,match='CONTEXT_MISMATCH'):
        same_identity(a,replace(a,**{field:value}))


@pytest.mark.parametrize('damage,code',[('columns','COLUMN_ORDER_ERROR'),('units','UNIT_ERROR'),
    ('grid','TIME_GRID_ERROR'),('future','FUTURE_INPUT'),('nan','NONFINITE_INPUT')])
def test_invalid_input_schema(reader,damage,code):
    contract=reader.registry.catalog['contracts']['D512']
    t=np.array([3600,3610]);x=np.ones((2,4));cols=list(contract['columns']);units=list(contract['units'])
    if damage=='columns': cols.reverse()
    if damage=='units': units[0]='kelvin'
    if damage=='grid': t[1]=3611
    if damage=='future': t[1]=4000
    if damage=='nan': x[0,0]=np.nan
    with pytest.raises(AdmissionError,match=code):validate_observations(t,x,cols,units,contract,3780)


def test_future_truncation_and_hash(reader):
    c=reader.read('D3:test_f14_00','D3',as_of=1980)
    d=reader.read('D3:test_f14_00','D3',as_of=1980)
    later=reader.read('D3:test_f14_00','D3',as_of=2160)
    assert c.observation_time==(1800,1980)
    assert c.input_hash==d.input_hash and c.context_id!=d.context_id
    assert later.input_hash!=c.input_hash
    assert np.array_equal(later.values[:2],c.values)
    assert stable_hash(np.array([np.nan,np.inf,-np.inf]))==stable_hash(np.array([np.nan,np.inf,-np.inf]))
    assert stable_hash(np.array([1],dtype='float64'))!=stable_hash(np.array([1],dtype='float32'))
    a=np.arange(12,dtype=float).reshape(3,4)
    assert stable_hash(a)==stable_hash(np.asfortranarray(a))
    assert stable_hash(a)!=stable_hash(a.reshape(4,3))


def test_future_observation_changes_do_not_change_input(reader,monkeypatch):
    c=reader.read('D3:test_f14_00','D3',as_of=1980)
    original=reader._raw
    def altered(path):
        t,x,u=original(path)
        x[t>1980]=123456.0
        u[t>1980]=99.0
        return t,x,u
    monkeypatch.setattr(reader,'_raw',altered)
    after=reader.read('D3:test_f14_00','D3',as_of=1980)
    assert c.input_hash==after.input_hash
    assert np.array_equal(c.values,after.values)


@pytest.mark.parametrize('as_of',[float('nan'),float('inf'),-1])
def test_invalid_server_clocks(reader,as_of):
    with pytest.raises(AdmissionError,match='INPUT_SCHEMA_ERROR'):
        reader.read('D3:test_f14_00','D3',as_of=as_of)


def test_model_window_cannot_be_substituted(reader):
    c=reader.read('D3:test_f14_00','D512',as_of=5400,window=600)
    e=reader.registry.entry('d512.static.1800')
    r=InferenceRequest('bad-window',c.context_id,e['model_id'],e['model_version'],'D512')
    with pytest.raises(AdmissionError,match='CONTRACT_MISMATCH'):reader.admit(r,c)


def test_forged_identity_rejected_even_with_recomputed_hash(reader):
    from causalverse.ai_runtime.provenance import context_payload
    c=reader.read('D3:test_f14_00','D3',as_of=1980)
    forged=replace(c,split='train')
    forged=replace(forged,input_hash=stable_hash(context_payload(forged)))
    e=reader.registry.entry('d3.pca')
    r=InferenceRequest('forged',c.context_id,e['model_id'],e['model_version'],'D3')
    with pytest.raises(AdmissionError,match='CONTEXT_MISMATCH'):reader.admit(r,forged)


@pytest.mark.parametrize('path',['../model.npz','D3:../test_f14_00', 'C:\\secret','D3:unknown','/etc/passwd'])
def test_forbidden_paths(reader,path):
    with pytest.raises(AdmissionError): reader.read(path,'D3',as_of=5400)


@pytest.mark.parametrize('field',['future_truth','hidden_valve','rng','fault_id','future_trajectory','path'])
def test_online_field_whitelist(field):
    with pytest.raises(AdmissionError,match='INPUT_SCHEMA_ERROR'):
        InferenceRequest.from_payload({field:[]})


@pytest.mark.parametrize('clock',[0,3770,3779])
def test_window_waits_for_end(reader,clock):
    with pytest.raises(AdmissionError,match='WINDOW_INCOMPLETE'):
        reader.read('D3:test_f14_00','D512',as_of=clock,window=180)


def test_admission_and_rejections_are_traced(reader,tmp_path):
    c=reader.read('D3:test_f14_00','D3',as_of=1980)
    e=reader.registry.entry('d3.pca')
    r=InferenceRequest('req',c.context_id,e['model_id'],e['model_version'],'D3')
    result,trace=trace_admission(lambda:reader.admit(r,c),request_id=r.request_id,model_id=r.model_id,
                                output_dir=tmp_path,context=c,entry=e)
    assert result['status']==trace['status']=='READY'
    _,bad=trace_admission(lambda:reader.admit(r,replace(c,run_id='wrong')),request_id='bad',
                         model_id=r.model_id,output_dir=tmp_path,context=c,entry=e)
    assert bad['status']=='REJECTED' and 'CONTEXT_MISMATCH' in bad['reason']
    _,wait=trace_admission(lambda:reader.read('D3:test_f14_00','D3',as_of=100),
                          request_id='early',model_id='d3.pca',output_dir=tmp_path)
    assert wait['status']=='WAITING'
    assert len(list(tmp_path.glob('*.json')))==3
    assert all(k in bad for k in ('inference_id','source_hash','model_hash','input_hash','contract_hash','elapsed_ms','cache_hit'))


def test_prediction_action_and_evaluation_separation(reader):
    c=reader.read('D511:test_631000_m14_a1','D511',as_of=5400)
    e=reader.registry.entry('d511.delta')
    r=InferenceRequest('r',c.context_id,e['model_id'],e['model_version'],'D511',action=1)
    assert reader.admit(r,c)['status']=='READY'
    for bad in (replace(r,action=2),replace(r,origin=5390),replace(r,duration_seconds=121),replace(r,horizons=(10,))):
        with pytest.raises(AdmissionError,match='ACTION_UNSUPPORTED'):reader.admit(bad,c)
    with pytest.raises(AdmissionError,match='INPUT_SCHEMA_ERROR'):
        reader.admit(r,EvaluationContext('eval',c.context_id,'reference',[]))


def test_no_forbidden_array_reads_or_calls(reader,monkeypatch):
    keys=[]
    original=np.lib.npyio.NpzFile.__getitem__
    allowed={'t_seconds','XMEAS','XMV','history','command','command_before','values'}
    def getitem(self,key):
        keys.append(key)
        assert key in allowed, f'forbidden online array {key}'
        return original(self,key)
    monkeypatch.setattr(np.lib.npyio.NpzFile,'__getitem__',getitem)
    def guard(frame,event,arg):
        if event=='call':
            assert frame.f_code.co_name not in ('fit','calibrate','set_control','inject_fault')
            assert '/simulation/' not in frame.f_code.co_filename.replace('\\','/')
    old=sys.getprofile()
    try:
        sys.setprofile(guard)
        reader.read('D3:test_f14_00','D3',as_of=1980)
        reader.read('D3:test_f14_00','D512',as_of=3780,window=180)
        reader.read('D511:test_631000_m14_a1','D511',as_of=5400)
    finally:sys.setprofile(old)
    assert keys and not (set(keys)-allowed)
