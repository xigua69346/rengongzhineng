import copy
import numpy as np
import pytest
from causalverse.simulation import TEPAdapter

def equal_rows(a,b):
    assert len(a.rows)==len(b.rows)
    for x,y in zip(a.rows,b.rows):
        for k in x:
            np.testing.assert_array_equal(x[k],y[k])

def test_snapshot_restore_and_aliases():
    a=TEPAdapter(123); a.inject_fault(11,onset_seconds=20); a.run(190)
    snap=a.snapshot(); a.run(190); expected=copy.deepcopy(a)
    a.restore(snap).run(190); equal_rows(a,expected)
    b=a.branch(); c=a.branch(); b.run(100); c.run(100); equal_rows(b,c)
    assert b.sim.process.state._process is b.sim.process
    assert b.sim.process is not c.sim.process
    assert snap.payload['sim'].step_count==190

def test_mapping_reset_validation():
    a=TEPAdapter(); assert a.get_measurements().shape==(41,)
    assert a.get_control_variables().shape==(12,)
    for i in (0,13,-1):
        with pytest.raises(ValueError): a.set_control(i,50,duration_seconds=2)
    with pytest.raises(ValueError): a.set_control(10,float('nan'),duration_seconds=2)
    with pytest.raises(ValueError): a.inject_fault(21)
    with pytest.raises(ValueError): a.run(-1)
    a.run(2); a.reset(); assert a.t_seconds==0 and not a.rows

def test_selective_controller_and_schedule():
    a=TEPAdapter(); a.run(120)
    a.set_control(10,50,start_seconds=130,duration_seconds=20)
    a.run(50)
    for r in a.rows[120:]:
        others=[i for i in range(12) if i!=9]
        np.testing.assert_array_equal(r['XMV'][others],r['pi_command'][others])
        assert r['XMV'][9]==(50 if 130<=r['t_seconds']<150 else r['pi_command'][9])
    assert np.ptp(np.array([r['XMV'] for r in a.rows[120:]])[:,0])>0

def test_seed_and_fault_onset():
    a=TEPAdapter(123); b=TEPAdapter(123); c=TEPAdapter(456)
    for sim in (a,b,c): sim.inject_fault(4,onset_seconds=10); sim.run(100)
    equal_rows(a,b)
    assert not np.array_equal(a.rows[-1]['XMEAS'],c.rows[-1]['XMEAS'])
    assert all(r['idv'][3]==int(r['t_seconds']>=10) for r in a.rows)

def test_export(tmp_path):
    a=TEPAdapter(); a.run(181); m=a.save(tmp_path)
    d=np.load(tmp_path/'trajectory.npz'); aligned=np.load(tmp_path/'aligned_180s.npz')
    assert d['XMEAS'].shape==(181,41) and d['XMV'].shape==(181,12)
    np.testing.assert_array_equal(aligned['t_seconds'],[0,180])
    assert m['backend']=='python'
