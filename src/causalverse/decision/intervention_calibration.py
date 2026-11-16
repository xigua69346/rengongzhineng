import numpy as np
from .uncertainty import conformal_radius

def calibrate(errors,scales):
    """errors: seed x mechanism x action x horizon x target.

    Returns normalized radii; all actions/targets/horizons share one joint score.
    """
    e=np.abs(errors)/scales
    joint=conformal_radius(e.max(axis=(1,2,3,4)),.9)
    action=conformal_radius(e.max(axis=(1,3,4)),.9)
    return float(joint),action

def intervals(mean,joint,action,scales,action_index):
    return (mean-joint*scales,mean+joint*scales),(mean-action[action_index]*scales,mean+action[action_index]*scales)
