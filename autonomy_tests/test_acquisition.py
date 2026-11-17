import numpy as np
import pytest
from causalverse.simulation import TEPAdapter
from causalverse.autonomy.acquisition import Acquisition
from causalverse.autonomy.contracts import validate
from causalverse.autonomy.journal import Journal,read_verified

def test_real_acquisition_and_freshness(tmp_path):
    sim=TEPAdapter();a=Acquisition('e');rows=[];j=Journal(tmp_path/'data.jsonl')
    for _ in range(1000):
        clock=sim.sim.time;gas=clock>=sim.sim.process._teproc.tgas or clock==0
        product=clock>=sim.sim.process._teproc.tprod or clock==0
        row=a.collect(sim.step(),clock);rows.append(row);j.append('observation',row)
        assert row['freshness']['gas_updated']==gas
        assert row['freshness']['product_updated']==product
        assert len(row['measurements'])==41 and len(row['commands'])==12
        assert not set(row)&{'idv','rng_state','valve_position','fault_schedule'}
    j.close();assert len(read_verified(j.path,995))==4
    assert rows[1]['freshness']['gas_updated'] is False
    assert rows[-1]['state_time']==1000

@pytest.mark.parametrize('kind',['missing','reorder','nan','cross','hash','column'])
def test_bad_observations(kind):
    row=Acquisition('e').collect(TEPAdapter().step())
    if kind=='missing':row.pop('commands')
    if kind=='reorder':row['seq']=1
    if kind=='nan':row['measurements'][0]=float('nan')
    if kind=='cross':row['episode_id']='other'
    if kind=='hash':row['payload_hash']='fake'
    if kind=='column':row['measurements'].pop()
    with pytest.raises(ValueError):validate(row,'e',0)

def test_journal_tampering(tmp_path):
    p=tmp_path/'j.jsonl';j=Journal(p);j.append('x',{'v':1});j.close()
    p.write_text(p.read_text().replace('"v": 1','"v": 2'))
    with pytest.raises(ValueError):read_verified(p)

def test_closed_journal_truncation_is_not_silently_accepted(tmp_path):
    p=tmp_path/'truncated.jsonl';p.write_text('{"seq":0')
    with pytest.raises(ValueError,match='TRUNCATED'):read_verified(p)
    assert read_verified(p,allow_partial=True)==[]
