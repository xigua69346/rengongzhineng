"""Small observational mechanism classifiers. Scores are not probabilities."""
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from causalverse.causal.dynamic import design, static_features, residual_features, MechanismEvidence

CLASSES=np.array([0,4,11,14])
NODES=('T9','C21','P7','U10')
STATISTICS=('mean','std','minimum','maximum','range','end_change','mean_absolute_speed','slope','late_minus_early')

def permitted_observations(measurements,commands):
    m=np.asarray(measurements);u=np.asarray(commands)
    if m.ndim!=2 or u.ndim!=2 or m.shape!=(len(u),41) or u.shape[1]!=12:raise ValueError('Expected separate 41 measurement / 12 command columns')
    x=np.column_stack([m[:,8],m[:,20],m[:,6],u[:,9]])
    if not np.isfinite(x).all():raise ValueError('Nonfinite observations')
    return x

def simple_features(x,dt=10.):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=4 or len(x)<3 or dt<=0 or not np.isfinite(x).all():raise ValueError('Need finite four-node time window')
    t=np.arange(len(x))*dt;t-=t.mean();third=max(1,len(x)//3)
    return np.concatenate([x.mean(0),x.std(0),x.min(0),x.max(0),np.ptp(x,axis=0),x[-1]-x[0],
        np.abs(np.diff(x,axis=0)).mean(0)/dt,t@x/(t@t),x[-third:].mean(0)-x[:third].mean(0)])

class SmallVAR:
    """Four-node unconstrained VAR, fixed D4 lag/ridge, normal training only."""
    def fit(self,runs,lag=6,alpha=.1):
        self.lag=lag;self.alpha=alpha;joined=np.concatenate(runs);self.mean=joined.mean(0);self.scale=np.maximum(joined.std(0),1e-8)
        z=[(x-self.mean)/self.scale for x in runs];a=np.concatenate([design(x,lag) for x in z]);y=np.concatenate([x[lag:] for x in z])
        penalty=np.eye(a.shape[1])*alpha;penalty[0,0]=0;self.coef=np.linalg.solve(a.T@a+penalty,a.T@y)
        self.noise=np.maximum((y-a@self.coef).std(0),1e-5);return self
    def residuals(self,x):
        z=(x-self.mean)/self.scale
        return (z[self.lag:]-design(z,self.lag)@self.coef)/self.noise

class LogisticMechanism:
    def fit(self,x,y):
        x=np.asarray(x);self.mean=x.mean(0);self.scale=np.maximum(x.std(0),1e-6)
        a=np.c_[np.ones(len(x)),(x-self.mean)/self.scale];labels=np.searchsorted(CLASSES,y)
        if not np.array_equal(CLASSES[labels],y):raise ValueError('Unknown offline label')
        target=np.eye(4)[labels]
        def objective(flat):
            w=flat.reshape(a.shape[1],4);z=a@w
            loss=np.sum(logsumexp(z,axis=1)-z[np.arange(len(z)),labels])+.5*np.sum(w[1:]**2)
            grad=a.T@(softmax(z,axis=1)-target);grad[1:]+=w[1:]
            return loss,grad.ravel()
        result=minimize(objective,np.zeros(a.shape[1]*4),jac=True,method='L-BFGS-B',options={'maxiter':1000,'ftol':1e-10})
        if not result.success:raise RuntimeError(result.message)
        self.coef=result.x.reshape(a.shape[1],4);self.iterations=int(result.nit);self.loss=float(result.fun);return self
    def scores(self,x):return softmax(np.c_[np.ones(len(x)),(x-self.mean)/self.scale]@self.coef,axis=1)

class CandidatePolicy:
    """Fixed per-class validation rank and conservative close-score expansion."""
    def fit(self,scores,labels):
        self.thresholds=[]
        for i,c in enumerate(CLASSES):
            values=np.sort(1-scores[np.asarray(labels)==c,i]);rank=int(np.ceil((len(values)+1)*.9))
            self.thresholds.append(float(values[rank-1]) if rank<=len(values) else float('inf'))
        self.thresholds=np.array(self.thresholds);return self
    def candidates(self,scores):
        sets=1-scores<=self.thresholds
        return conservative_candidates(scores,sets)

def conservative_candidates(scores,sets):
    sets=sets.copy();rank=np.argsort(-scores,axis=1)
    for i,r in enumerate(rank):
        if scores[i,r[0]]-scores[i,r[1]]<.05:sets[i,r[:2]]=True
        if sets[i].sum()==1 and not sets[i,r[0]]:sets[i,r[0]]=True
    return rank,sets

def summarize(labels,rank,sets):
    labels=np.asarray(labels);prediction=CLASSES[rank[:,0]];cm=np.zeros((4,4),int)
    for y,p in zip(labels,prediction):cm[np.searchsorted(CLASSES,y),np.searchsorted(CLASSES,p)]+=1
    precision=np.diag(cm)/np.maximum(cm.sum(0),1);recall=np.diag(cm)/np.maximum(cm.sum(1),1)
    f1=2*precision*recall/np.maximum(precision+recall,1e-12);certain=sets.sum(1)==1;chosen=CLASSES[np.argmax(sets,axis=1)]
    return dict(n=len(labels),top1=float(np.mean(prediction==labels)),macro_f1=float(f1.mean()),
        top2=float(np.mean([y in CLASSES[r[:2]] for y,r in zip(labels,rank)])),refusal=float(np.mean(~certain)),
        candidate_coverage=float(np.mean(sets[np.arange(len(labels)),np.searchsorted(CLASSES,labels)])),
        wrong_certain_all=float(np.mean(certain&(chosen!=labels))),confusion_matrix=cm.tolist(),
        per_class={str(c):dict(n=int(cm[i].sum()),precision=float(precision[i]),recall=float(recall[i]),f1=float(f1[i]),
            refusal=float(np.mean(~certain[labels==c]))) for i,c in enumerate(CLASSES)})
