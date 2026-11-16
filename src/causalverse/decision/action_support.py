import numpy as np

class ActionSupport:
    def fit(self,histories):
        x=np.array(histories);self.lower=x.min(axis=(0,1));self.upper=x.max(axis=(0,1));self.scale=np.maximum(x.std(axis=(0,1)),1e-6)
        return self
    def check(self,history,delta,duration,horizon,disagreement,radius=None,command=None):
        h=np.asarray(history);reasons=[]
        if h.shape!=(6,7) or not np.isfinite(h).all():reasons.append('invalid_complete_history')
        else:
            if np.any((h<self.lower-3*self.scale)|(h>self.upper+3*self.scale)):reasons.append('history_or_command_outside_support')
            current=h[-1,5] if command is None else command
            if not np.isfinite(current) or not 0<=current+delta<=100:reasons.append('command_saturation')
        if delta not in (0,1,5) or duration!=120:reasons.append('untrained_action')
        if horizon not in (10,30,60,120,300,600):reasons.append('uncalibrated_horizon')
        if not np.isfinite(disagreement) or disagreement>1:reasons.append('ensemble_disagreement')
        if radius is not None and (not np.isfinite(radius) or radius>=1):reasons.append('recursive_instability')
        return dict(supported=not reasons,reasons=reasons,optimization_allowed=False)

def candidate_disagreement(predictions,scales):
    """Maximum standardized range across every candidate, horizon and target."""
    x=np.asarray(predictions,dtype=float);s=np.asarray(scales,dtype=float)
    if x.ndim!=3 or x.shape[0]<2 or x.shape[2]!=len(s) or not np.isfinite(x).all() or np.any(s<=0):
        return float('inf')
    return float(np.max(np.ptp(x,axis=0)/s))
