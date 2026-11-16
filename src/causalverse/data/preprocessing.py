import numpy as np

MEASUREMENTS=tuple(f'XMEAS({i})' for i in range(1,42))
CONTROLS=tuple(f'XMV({i})' for i in range(1,13))

def validate(t, measurements, controls, expected_length=None):
    t=np.asarray(t)
    if t.ndim!=1 or len(t)==0 or not np.array_equal(t,np.arange(len(t))):
        raise ValueError('Expected complete integer one-second trajectory from zero')
    if expected_length is not None and len(t)!=expected_length:
        raise ValueError('Incomplete trajectory; retain raw failure for review')
    if measurements.shape!=(len(t),41) or controls.shape!=(len(t),12):
        raise ValueError('Incorrect variable mapping')
    if not all(np.isfinite(a).all() for a in (t,measurements,controls)):
        raise ValueError('NaN/Inf/missing values; no silent imputation')

def process(t, measurements, controls, fault_id, onset, warmup=1800, interval=180):
    validate(t,measurements,controls)
    mask=(t>=warmup)&(t%interval==0)
    return dict(t_seconds=t[mask],XMEAS=measurements[mask],XMV=controls[mask],
                y=((t[mask]>=onset)&(fault_id!=0)).astype(np.int8))

def windows(x, length):
    """Call separately per run; never join boundaries or splits."""
    if length<1 or length>len(x): raise ValueError('Invalid window length')
    return np.stack([x[i:i+length] for i in range(len(x)-length+1)])

class Standardizer:
    def fit(self,x):
        if x.ndim!=2 or not np.isfinite(x).all(): raise ValueError('Invalid training matrix')
        self.mean=x.mean(axis=0); self.scale=x.std(axis=0,ddof=1)
        self.constant=self.scale<1e-12
        self.scale[self.constant]=1.0
        return self
    def transform(self,x):
        if x.shape[1]!=len(self.mean) or not np.isfinite(x).all(): raise ValueError('Invalid input')
        return (x-self.mean)/self.scale
