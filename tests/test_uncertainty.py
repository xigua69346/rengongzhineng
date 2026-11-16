import numpy as np
import pytest
from causalverse.decision.uncertainty import (bootstrap_runs,residual_blocks,conformal_radius,physical_coefficients,
    MechanismEnsemble,evaluate_all_mechanisms,trust_state,support_check)

def test_bootstrap_resamples_whole_runs():
    runs=[np.full((10,7),i,dtype=float) for i in range(20)]
    sample,ids=bootstrap_runs(runs,np.random.default_rng(9))
    assert len(sample)==20
    for a,i in zip(sample,ids):assert a is runs[i] and a.shape==(10,7)
    _,ids2=bootstrap_runs(runs,np.random.default_rng(9));np.testing.assert_array_equal(ids,ids2)

def test_joint_blocks_preserve_time_and_node_dependence():
    banks=[np.arange(100)[:,None]+np.arange(7)[None,:]*1000+i*100000 for i in range(3)]
    out,meta=residual_blocks(banks,31,4,12,np.random.default_rng(8))
    for path in range(4):
        t=0
        for run,start,length in meta[path]:
            np.testing.assert_array_equal(out[path,t:t+length],banks[run][start:start+length]);t+=length
    with pytest.raises(ValueError):residual_blocks([np.zeros((3,7))],4,2,12,np.random.default_rng())

def test_conformal_run_scores_and_small_sample_limit():
    assert conformal_radius(np.arange(10))==9
    assert np.isinf(conformal_radius(np.arange(3)))
    a=np.arange(60).reshape(10,2,3);np.testing.assert_array_equal(conformal_radius(a),a[-1])
    with pytest.raises(ValueError):conformal_radius([])

def test_forecast_reproducible_and_uses_history_only(tmp_path):
    rng=np.random.default_rng(6);runs=[rng.normal(size=(100,7)) for _ in range(4)]
    e=MechanismEnsemble(3,lag=1,block_length=3).fit(runs,7);history=runs[0][-2:]
    a=e.forecast(history,6,seed=9);b=e.forecast(history,6,seed=9)
    np.testing.assert_array_equal(a['samples'],b['samples'])
    assert not np.array_equal(a['samples'],e.forecast(history,6,seed=10)['samples'])
    combined=evaluate_all_mechanisms([e,e],history,6,seed=9)
    assert combined['lower'].shape==(6,7) and np.all(combined['upper']>=combined['lower'])
    with pytest.raises(TypeError):e.forecast(history,true_idv=14)
    e.save(tmp_path/'ensemble.npz');assert (tmp_path/'ensemble.npz').exists()
    assert not support_check([e],np.full((2,7),1e12))['supported']

def test_wide_intervals_and_bad_coverage_cannot_authorize_optimization():
    bad=trust_state(.99,.1,100,.25,1,10)
    assert bad['state']=='不可信' and 'interval_too_wide' in bad['reasons']
    good=trust_state(.95,.1,.5,.25,1,10)
    assert good['state'].startswith('可信') and not good['optimization_allowed']
    assert 'coverage_below_90_percent' in trust_state(.85,.1,.5,.25,1,10)['reasons']
    assert 'insufficient_independent_calibration_runs' in trust_state(.95,.1,.5,.25,1,3)['reasons']

def test_bootstrap_parameter_units_are_comparable():
    rng=np.random.default_rng(31);runs=[rng.normal(size=(50,7))*np.arange(1,8)+10 for _ in range(4)]
    e=MechanismEnsemble(2,lag=2,block_length=3).fit(runs,8);m=e.models[0]
    h=runs[0][-2:];row=np.r_[1.,h[-1],h[-2]]
    np.testing.assert_allclose(row@physical_coefficients(m),m.predict_next(h),atol=1e-10)

def test_completed_experiment_split_and_history_protection():
    from pathlib import Path
    import json
    from causalverse.data.manifest import digest
    root=Path('artifacts/d5/uncertainty')
    if not (root/'execution.json').exists():pytest.skip('Full D5.1 integration outputs not generated')
    p=json.loads((root/'protocol.json').read_text());members=json.loads((root/'ensemble_manifest.json').read_text())
    calibration=json.loads((root/'calibration_manifest.json').read_text())
    train={r['dataset_run_id'] for r in p['runs'] if r['split']=='train'}
    val={r['dataset_run_id'] for r in p['runs'] if r['split']=='validation'}
    test={r['dataset_run_id'] for r in p['runs'] if r['split']=='test'}
    assert not (train&val or train&test or val&test)
    assert all(set(m['fit_runs'])<=train for m in members)
    assert set(calibration['run_ids'])==val
    old=json.loads((root/'protected_before.json').read_text())
    assert all(digest(path)==h for path,h in old.items())
