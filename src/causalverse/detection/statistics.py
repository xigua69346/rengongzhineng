import numpy as np

def control_limit(values,quantile):
    if not 0<quantile<1 or not np.isfinite(values).all(): raise ValueError('Invalid calibration')
    return max(float(np.quantile(values,quantile,method='higher')),1e-12)
