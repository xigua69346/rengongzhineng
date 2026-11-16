import numpy as np
import pytest
from causalverse.decision.intervention_calibration import calibrate
from causalverse.decision.action_support import ActionSupport,candidate_disagreement
from causalverse.decision.intervention_model import action_features,ConditionalPredictor

def test_joint_calibration_controls_action_selection():
    e=np.zeros((20,4,3,6,3));e[:,0,2,5,2]=np.arange(20)
    q,qa=calibrate(e,np.ones(3));assert q==18 and qa[0]==0 and qa[2]==18
    assert np.all(np.max(e,axis=(1,2,3,4))<=19)

def test_complete_window_and_action_support():
    rng=np.random.default_rng(8);h=rng.normal(size=(30,6,7));s=ActionSupport().fit(h)
    x=h[0].copy();x[0,0]=1e10
    assert not s.check(x,1,120,600,0)['supported']
    for delta,duration,horizon in [(10,120,600),(1,300,600),(1,120,900)]:assert not s.check(h[0],delta,duration,horizon,0)['supported']
    assert not s.check(h[0],1,120,600,2)['supported']
    assert not s.check(h[0],1,120,600,0,radius=1.001)['supported']
    assert not s.check(h[0],1,120,600,0,radius=float('nan'))['supported']
    assert not s.check(h[0],5,120,600,0,command=99)['supported']

def test_model_has_no_hidden_state_inputs():
    h=np.ones((6,7))
    with pytest.raises(ValueError):action_features(h,20)
    with pytest.raises(TypeError):ConditionalPredictor().predict(h,1,true_idv=14)
    assert action_features(h,1,command=10).shape==action_features(h,5,command=10).shape

def test_all_candidates_disagreement():
    x=np.zeros((4,6,3));x[3,0,1]=4
    assert candidate_disagreement(x,[.25,.5,5])==8
    x[0,0,0]=np.nan
    assert np.isinf(candidate_disagreement(x,[.25,.5,5]))
