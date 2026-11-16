import numpy as np
import pytest
from causalverse.dashboard.server import api,trajectory,diagnosis,uncertainty

def test_hmi_local_alarm_scores_reuse_saved_threshold_outputs():
    from causalverse.dashboard.server import detection,ROOT
    result=detection('test_f14_00')
    with np.load(ROOT/'artifacts/d3/detection/test_f14_00.npz') as saved:
        np.testing.assert_equal(result['variable_threshold_scores'],saved['threshold_contribution'])

def test_saved_trajectory_schema_and_no_hidden_inputs():
    data=trajectory('test_f14_00');assert len(data['time'])==14400
    assert np.asarray(data['values']).shape==(14400,4)
    assert np.isfinite(data['values']).all()
    with pytest.raises(ValueError):trajectory('../../pyproject.toml')

def test_diagnosis_matches_historical_run_and_window():
    d=diagnosis('test_f14_00','VAR',1800)
    assert d['run_id']=='test_f14_00' and d['optimization_allowed'] is False
    with pytest.raises(ValueError):diagnosis('test_f14_00','VAR',300)

def test_uncertainty_trace_identity_and_bounds():
    d=uncertainty('delta',631019,14,5)
    assert np.asarray(d['truth']).shape==(6,3)
    assert np.all(np.asarray(d['joint_lower'])<=np.asarray(d['joint_upper']))
    assert d['trusted_for_optimization'] is False
    with pytest.raises(ValueError):uncertainty('delta',631000,14,10)
    with pytest.raises(KeyError):api('/api/set_control',{})
