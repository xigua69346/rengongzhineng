"""Checks real D5.1.1 saved splits/calibration and prediction isolation."""
import json
from pathlib import Path
import numpy as np
from causalverse.decision.intervention_calibration import calibrate
from causalverse.decision.intervention_model import ConditionalPredictor

R=Path('artifacts/d5_1_1')

def test_independent_seed_units_and_all_branches():
    p=json.loads((R/'protocol.json').read_text());sets=[set(v) for v in p['seeds'].values()]
    assert all(len(s)==20 for s in sets)
    assert all(not a&b for i,a in enumerate(sets) for b in sets[i+1:])
    log=json.loads((R/'data_log.json').read_text())['runs'];assert len(log)==720
    for split,seeds in p['seeds'].items():
        for seed in seeds:
            rows=[r for r in log if r['seed']==seed and r['split']==split]
            assert {(r['mechanism'],r['delta']) for r in rows}=={(m,a) for m in (0,4,11,14) for a in (0,1,5)}
            assert all(r['rng_paired'] and r['records']==6121 and r['termination'] is None for r in rows)

def test_saved_independent_calibration_is_reproducible():
    for kind in ('action','delta','PI','PI_stable'):
        d=np.load(R/f'predictions_{kind}_calibration.npz');e=(d['truth']-d['predicted']).reshape(20,4,3,6,3)
        q,qa=calibrate(e,np.array([.25,.5,5.]));saved=json.loads((R/f'calibration_{kind}.json').read_text())
        np.testing.assert_equal(q,saved['joint']);np.testing.assert_equal(qa,saved['actionwise'])
        assert np.isfinite(d['predicted']).all()

def test_delta_prediction_does_not_need_future_baseline():
    rng=np.random.default_rng(10);rows=[]
    for i in range(20):
        h=rng.normal(size=(6,7))
        for a in (0,1,5):rows.append(dict(history=h,delta=a,command_before=20.,truth=np.ones((6,3))*a,delta_truth=np.ones((6,3))*a))
    m=ConditionalPredictor('delta').fit(rows);h=rows[0]['history'].copy();before=m.predict(h,1,20.)
    for r in rows:r['truth'][:]=1e9;r['delta_truth'][:]=-1e9
    np.testing.assert_equal(before,m.predict(h,1,20.))
