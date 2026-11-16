import numpy as np
import pytest
from causalverse.data.preprocessing import validate,process,windows,Standardizer

def test_shapes_missing_and_alignment():
    t=np.arange(541);x=np.ones((541,41));u=np.ones((541,12))
    d=process(t,x,u,4,180,warmup=0)
    np.testing.assert_array_equal(d['t_seconds'],[0,180,360,540]);np.testing.assert_array_equal(d['y'],[0,1,1,1])
    with pytest.raises(ValueError):validate(t[1:],x[1:],u[1:])
    with pytest.raises(ValueError):validate(t,x[:,:40],u)
    x[1,1]=np.nan
    with pytest.raises(ValueError):validate(t,x,u)

def test_standardizer_and_windows():
    train=np.array([[1.,3],[2,3],[3,3]])
    s=Standardizer().fit(train); before=s.mean.copy();s.transform(np.array([[1000.,3]]))
    np.testing.assert_array_equal(s.mean,before)
    assert s.constant[1] and windows(train,2).shape==(2,2,2)
