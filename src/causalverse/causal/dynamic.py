import numpy as np

NAMES=['T9','C21','P7','L8','F6','U10','U4']
# Reduced observed graph: several paths are mediated by unobserved plant states.
PARENTS=[[0,1,2,3,4],[0,1,5],[0,2,3,4],[3,4,6],[4,6],[0,1,5],[3,6]]

def observed(measurements,controls):
    if measurements.shape[1]!=41 or controls.shape[1]!=12: raise ValueError('Bad observation schema')
    return np.column_stack([measurements[:,8],measurements[:,20],measurements[:,6],measurements[:,7],measurements[:,5],controls[:,9],controls[:,3]])

def design(x,lag):
    if len(x)<=lag: raise ValueError('Insufficient history')
    return np.column_stack([np.ones(len(x)-lag),*[x[lag-k:len(x)-k] for k in range(1,lag+1)]])

class DynamicModel:
    def __init__(self,lag=1,alpha=1.,constrained=True):
        self.lag=lag;self.alpha=alpha;self.constrained=constrained
    def fit(self,runs):
        joined=np.concatenate(runs);self.mean=joined.mean(0);self.scale=np.maximum(joined.std(0),1e-8)
        x=[(a-self.mean)/self.scale for a in runs]
        X=np.concatenate([design(a,self.lag) for a in x]);Y=np.concatenate([a[self.lag:] for a in x])
        self.coef=np.zeros((1+7*self.lag,7))
        for j in range(7):
            parents=PARENTS[j] if self.constrained else list(range(7))
            ids=[0]+[1+(k-1)*7+i for k in range(1,self.lag+1) for i in parents]
            A=X[:,ids];pen=np.eye(len(ids))*self.alpha;pen[0,0]=0
            self.coef[ids,j]=np.linalg.solve(A.T@A+pen,A.T@Y[:,j])
        self.noise=np.maximum(np.std(Y-X@self.coef,axis=0),1e-5)
        return self
    def residuals(self,x):
        z=(x-self.mean)/self.scale
        return (z[self.lag:]-design(z,self.lag)@self.coef)/self.noise
    def predict_next(self,history):
        z=(np.asarray(history[-self.lag:])-self.mean)/self.scale
        a=np.r_[1.,*[z[-k] for k in range(1,self.lag+1)]]
        return (a@self.coef)*self.scale+self.mean
    def rollout(self,history,steps,override=None):
        h=list(np.asarray(history).copy());out=[]
        for k in range(steps):
            row=self.predict_next(h)
            if override is not None and k<override['steps']:row[5]=override['value']
            out.append(row);h.append(row)
        return np.array(out)

def residual_features(model,x):
    r=model.residuals(x)
    return np.r_[r.mean(0),np.log1p(np.mean(r*r,axis=0)),
                 np.mean(r[1:]*r[:-1],axis=0)/(np.mean(r*r,axis=0)+1e-8)]

def static_features(x):return np.r_[x.mean(0),np.log(np.maximum(x.std(0),1e-8))]

class MechanismEvidence:
    """Supervised residual signature likelihood proxy, not identified causes."""
    def fit(self,features,labels):
        self.center=np.mean(features,0);self.scale=np.maximum(np.std(features,0),1e-6)
        z=(features-self.center)/self.scale
        self.means=np.array([z[labels==c].mean(0) for c in (0,4,11,14)])
        self.variances=np.array([np.maximum(z[labels==c].var(0),.1) for c in (0,4,11,14)])
        return self
    def distances(self,features):
        z=(features-self.center)/self.scale
        return np.mean((z[:,None,:]-self.means)**2/self.variances,axis=2)
    def calibrate(self,features,labels):
        d=self.distances(features);self.limits=[]
        for i,c in enumerate((0,4,11,14)):
            scores=np.sort(d[labels==c,i]);rank=int(np.ceil((len(scores)+1)*.9))
            # Infinite conformal quantile when calibration set is too small.
            self.limits.append(float(scores[rank-1]) if rank<=len(scores) else np.finfo(float).max)
        self.limits=np.array(self.limits);return self
    def diagnose(self,features):
        d=self.distances(features)
        return np.argsort(d,axis=1),d<=self.limits,d
