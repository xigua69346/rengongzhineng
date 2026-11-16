import json
from pathlib import Path
import numpy as np
import pytest
from causalverse.decision.mechanism import (permitted_observations,simple_features,LogisticMechanism,
    CandidatePolicy,conservative_candidates,summarize)

def test_physical_mapping_and_timed_features():
    m=np.tile(np.arange(41),(18,1));u=np.tile(np.arange(12),(18,1))
    np.testing.assert_equal(permitted_observations(m,u)[0],[8,20,6,9])
    x=np.tile((np.arange(18)*10.)[:,None],(1,4));f=simple_features(x).reshape(9,4)
    np.testing.assert_allclose(f[6:8],1)
    with pytest.raises(ValueError):simple_features(np.zeros((18,5)))
    with pytest.raises(TypeError):simple_features(x,true_idv=14)

def test_logistic_scores_reproducible_and_close_candidates_refused():
    rng=np.random.default_rng(5);y=np.repeat([0,4,11,14],20);x=np.repeat(np.eye(4)*10,20,axis=0)+rng.normal(size=(80,4))*.1
    m=LogisticMechanism().fit(x,y);s=m.scores(x)
    assert np.mean(np.argmax(s,axis=1)==np.repeat(np.arange(4),20))==1
    assert np.isfinite(s).all()
    rank,sets=conservative_candidates(np.array([[.4,.39,.11,.1]]),np.array([[True,False,False,False]]))
    assert sets.sum()==2
    p=CandidatePolicy().fit(np.ones((4,4))*.25,np.array([0,4,11,14]))
    assert np.isinf(p.thresholds).all()  # too few validation runs never force a singleton

def test_metrics_and_frozen_run_units():
    r=np.array([[0,1,2,3],[1,0,2,3],[2,0,1,3],[3,0,1,2]])
    m=summarize(np.array([0,4,11,14]),r,np.eye(4,dtype=bool));assert m['macro_f1']==1 and m['top2']==1 and m['refusal']==0
    p=Path('artifacts/d5_1_2/protocol.json')
    if not p.exists():pytest.skip('Run D5.1.2 freeze for artifact integration check')
    plan=json.loads(p.read_text());groups=[{r['seed'] for r in plan['d3_runs'] if r['split']==s} for s in ('train','validation','test')]
    ext=plan['external_runs'];groups.append({r['seed'] for r in ext})
    assert [len(g) for g in groups]==[80,40,80,20]
    assert len(ext)==80 and all(r['delta']==0 for r in ext)
    assert all(not a&b for i,a in enumerate(groups) for b in groups[i+1:])
