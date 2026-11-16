import numpy as np
from causalverse.detection.pca import PCADetector
from causalverse.detection.threshold import ThresholdDetector
from causalverse.detection.statistics import control_limit

def test_pca_statistics_and_conservation():
    rng=np.random.default_rng(1);z=rng.normal(size=(500,6));z[:,5]=z[:,0]+.01*z[:,5]
    p=PCADetector().fit(z);s=p.scores(z)
    np.testing.assert_allclose(s['T2_contribution'].sum(axis=1),s['T2'],rtol=1e-12)
    np.testing.assert_allclose(s['SPE_contribution'].sum(axis=1),s['SPE'])
    assert np.cumsum(p.ratio)[len(p.components)-1]>=.9
    assert control_limit(s['T2'],.995)>0

def test_threshold_spike():
    rng=np.random.default_rng(1);z=rng.normal(size=(200,5));d=ThresholdDetector().fit(z)
    assert d.score(np.ones((1,5))*100)[0]>d.score(z).max()
