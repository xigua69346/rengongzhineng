"""Direct finite-horizon conditional predictors; no latent simulator inputs."""
import numpy as np

def history_features(history):
    h=np.asarray(history)
    if h.shape!=(6,7) or not np.isfinite(h).all():raise ValueError('Need complete six-step seven-node history')
    return np.r_[h[-1],h.mean(0),h.std(0),h[-1]-h[0],np.diff(h[:,5])]

class Ridge:
    def fit(self,x,y):
        self.mean=x.mean(0);self.scale=np.maximum(x.std(0),1e-6)
        a=np.c_[np.ones(len(x)),(x-self.mean)/self.scale];p=np.eye(a.shape[1])*10;p[0,0]=0
        self.coef=np.linalg.solve(a.T@a+p,a.T@y);return self
    def predict(self,x):return np.c_[np.ones(len(x)),(x-self.mean)/self.scale]@self.coef

def action_features(history,delta,duration=120,command=None):
    if delta not in (0,1,5) or duration!=120:raise ValueError('Action outside validated definition')
    h=history_features(history)
    # Horizon-specific output heads encode active/ended phase at fixed horizons.
    current=history[-1,5] if command is None else command
    return np.r_[h,current,current-history[-1,5],delta,delta*delta,h*delta,h*(delta==5),duration/120]

class ConditionalPredictor:
    def __init__(self,kind='action'):self.kind=kind
    def fit(self,rows):
        if self.kind=='action':
            x=np.array([action_features(r['history'],r['delta'],command=r['command_before']) for r in rows]);y=np.array([(r['truth']-r['history'][-1,:3]).ravel() for r in rows])
            self.model=Ridge().fit(x,y)
        else:
            base=[r for r in rows if r['delta']==0]
            self.base=Ridge().fit(np.array([history_features(r['history']) for r in base]),np.array([(r['truth']-r['history'][-1,:3]).ravel() for r in base]))
            self.model=Ridge().fit(np.array([action_features(r['history'],r['delta'],command=r['command_before']) for r in rows]),np.array([r['delta_truth'].ravel() for r in rows]))
        return self
    def predict(self,history,delta,command=None):
        f=action_features(history,delta,command=command)[None,:]
        if self.kind=='action':return self.model.predict(f).reshape(6,3)+history[-1,:3]
        base=self.base.predict(history_features(history)[None,:]).reshape(6,3)+history[-1,:3]
        return base+(self.model.predict(f).reshape(6,3) if delta else 0)
