import numpy as np
from causalverse.causal.dynamic import DynamicModel,MechanismEvidence,design,observed

def test_lag_design_does_not_cross_runs():
    a=np.arange(35.).reshape(5,7);x=design(a,2)
    np.testing.assert_array_equal(x[0,1:8],a[1]);np.testing.assert_array_equal(x[0,8:],a[0])
    assert len(x)==3

def test_input_allowlist():
    m=np.ones((5,41));u=np.ones((5,12))*2
    o=observed(m,u);assert o.shape==(5,7)
    np.testing.assert_array_equal(o[:,:5],1);np.testing.assert_array_equal(o[:,5:],2)

def test_conformal_insufficient_calibration_refuses_certainty():
    rng=np.random.default_rng(0);y=np.repeat([0,4,11,14],4);x=rng.normal(size=(16,3))
    e=MechanismEvidence().fit(x,y).calibrate(x,y)
    _,s,_=e.diagnose(x);assert np.all(s)  # n=4 cannot support finite .9 class threshold

def test_synthetic_known_dynamic_edges():
    rng=np.random.default_rng(42);x=np.zeros((4000,7))
    for t in range(1,len(x)):
        x[t]=.4*x[t-1]+rng.normal(size=7)
        x[t,1:]+=.3*x[t-1,:-1]
    m=DynamicModel(1,.1,False).fit([x])
    weights=m.coef[1:];found=np.abs(weights)>.15;np.fill_diagonal(found,False)
    true=np.zeros((7,7),bool)
    for j in range(6):true[j,j+1]=True
    assert np.array_equal(found,true)

def test_rollout_intervention_time_alignment():
    m=DynamicModel(1);m.mean=np.zeros(7);m.scale=np.ones(7);m.coef=np.zeros((8,7));m.coef[6,0]=1
    h=np.zeros((1,7));h[0,5]=3
    p=m.rollout(h,2,dict(value=3,steps=1))
    assert p[0,0]==3 and p[1,0]==3
