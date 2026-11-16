"""Run-bootstrap ensembles and multivariate time-block residual forecasts.

No IDV, RNG or hidden simulator state is an inference argument. Mechanism IDs
are training groups; inference always evaluates all four candidate mechanisms.
"""
import numpy as np
from causalverse.causal.dynamic import DynamicModel,design

def physical_coefficients(model):
    """Express bootstrap parameters in a common physical-unit coordinate system."""
    coef=model.coef.copy()
    for row in range(1,len(coef)):
        source=(row-1)%7
        coef[row]=model.coef[row]*model.scale/model.scale[source]
    coef[0]=model.mean+model.coef[0]*model.scale
    for row in range(1,len(coef)):
        coef[0]-=coef[row]*model.mean[(row-1)%7]
    return coef

def bootstrap_runs(runs,rng):
    ids=rng.integers(0,len(runs),len(runs))
    return [runs[i] for i in ids],ids

def residual_blocks(banks,steps,count,block_length,rng):
    if min(steps,count,block_length)<1:raise ValueError('Positive dimensions required')
    if not banks or any(a.ndim!=2 or a.shape[1]!=7 or len(a)<block_length for a in banks):
        raise ValueError('Insufficient complete residual blocks')
    result=np.empty((count,steps,7));lineage=[]
    for path in range(count):
        meta=[]
        for t in range(0,steps,block_length):
            run=int(rng.integers(len(banks)));start=int(rng.integers(len(banks[run])-block_length+1))
            length=min(block_length,steps-t)
            result[path,t:t+length]=banks[run][start:start+length]
            meta.append((run,start,length))
        lineage.append(meta)
    return result,lineage

def conformal_radius(run_scores,coverage=.9):
    a=np.asarray(run_scores,dtype=float)
    if a.ndim<1 or len(a)==0 or not np.isfinite(a).all() or not 0<coverage<1:
        raise ValueError('Invalid calibration scores')
    rank=int(np.ceil((len(a)+1)*coverage))
    if rank>len(a):return np.full(a.shape[1:],np.inf)
    return np.sort(a,axis=0)[rank-1]

class MechanismEnsemble:
    def __init__(self,members=20,lag=6,alpha=.1,block_length=12):
        self.members=members;self.lag=lag;self.alpha=alpha;self.block_length=block_length
    def fit(self,runs,seed):
        if len(runs)<2 or self.members<2:raise ValueError('Need multiple runs and members')
        rng=np.random.default_rng(seed);self.models=[];self.bootstrap_ids=[]
        for _ in range(self.members):
            sample,ids=bootstrap_runs(runs,rng)
            self.models.append(DynamicModel(self.lag,self.alpha,True).fit(sample));self.bootstrap_ids.append(ids)
        pooled=DynamicModel(self.lag,self.alpha,True).fit(runs)
        # Residual vectors stay joint across all seven nodes, in physical units.
        self.banks=[]
        for x in runs:
            z=(x-pooled.mean)/pooled.scale
            self.banks.append((z[self.lag:]-design(z,self.lag)@pooled.coef)*pooled.scale)
        center=np.concatenate(self.banks).mean(0)
        self.banks=[r-center for r in self.banks]
        joined=np.concatenate(runs);self.lower=np.quantile(joined,.001,axis=0);self.upper=np.quantile(joined,.999,axis=0)
        self.support_scale=np.maximum(joined.std(0),1e-6)
        return self
    def save(self,path):
        np.savez_compressed(path,coef=[m.coef for m in self.models],mean=[m.mean for m in self.models],
                            scale=[m.scale for m in self.models],bootstrap_ids=self.bootstrap_ids,
                            residual_banks=np.stack(self.banks),lower=self.lower,upper=self.upper,support_scale=self.support_scale)
    def forecast(self,history,steps=60,process_replicas=2,seed=0,override=None):
        history=np.asarray(history,dtype=float)
        if history.ndim!=2 or history.shape[1]!=7 or len(history)<self.lag or not np.isfinite(history).all():
            raise ValueError('History must contain finite permitted seven-node observations')
        if steps<1 or process_replicas<1:raise ValueError('Positive horizon and replicas required')
        ids=np.repeat(np.arange(len(self.models)),process_replicas);count=len(ids)
        mean=np.array([self.models[i].mean for i in ids]);scale=np.array([self.models[i].scale for i in ids]);coef=np.array([self.models[i].coef for i in ids])
        h=np.repeat(history[None,-self.lag:,:],count,axis=0).copy()
        # override describes only a previously tested D4 command; not an optimizer.
        if override is not None:h[:,-1,5]=override['value']
        errors,lineage=residual_blocks(self.banks,steps,count,self.block_length,np.random.default_rng(seed))
        samples=[];deterministic=[]
        hd=h.copy()
        for t in range(steps):
            feature=np.concatenate([np.ones((count,1)),*((h[:,-k]-mean)/scale for k in range(1,self.lag+1))],axis=1)
            fd=np.concatenate([np.ones((count,1)),*((hd[:,-k]-mean)/scale for k in range(1,self.lag+1))],axis=1)
            row=np.einsum('bi,bij->bj',feature,coef)*scale+mean+errors[:,t]
            rd=np.einsum('bi,bij->bj',fd,coef)*scale+mean
            if override is not None and (t+1)*10<override['duration_seconds']:
                row[:,5]=override['value'];rd[:,5]=override['value']
            h=np.concatenate([h[:,1:],row[:,None]],axis=1);hd=np.concatenate([hd[:,1:],rd[:,None]],axis=1)
            samples.append(row);deterministic.append(rd)
        return dict(samples=np.array(samples).transpose(1,0,2),parameter_only=np.array(deterministic).transpose(1,0,2),lineage=lineage)

def evaluate_all_mechanisms(ensembles,history,steps=60,seed=0,override=None):
    forecasts=[m.forecast(history,steps,seed=seed+i*10000,override=override) for i,m in enumerate(ensembles)]
    samples=np.array([r['samples'] for r in forecasts])
    low=np.quantile(samples,.05,axis=1);high=np.quantile(samples,.95,axis=1)
    return dict(lower=low.min(axis=0),upper=high.max(axis=0),
                mean=np.mean([r['parameter_only'].mean(axis=0) for r in forecasts],axis=0),
                mechanism_means=np.array([r['parameter_only'].mean(axis=0) for r in forecasts]),
                conditional_lower=low,conditional_upper=high,
                parameter_std=np.array([r['parameter_only'].std(axis=0) for r in forecasts]),
                total_std=np.array([r['samples'].std(axis=0) for r in forecasts]))

def support_check(ensembles,history):
    # A history can be supported by any candidate, not by a supplied true label.
    counts=[int(np.sum((history[-1]<e.lower-3*e.support_scale)|(history[-1]>e.upper+3*e.support_scale))) for e in ensembles]
    return dict(supported=any(n==0 for n in counts),outside_dimensions_by_candidate=counts)

def trust_state(coverage,mae,width,mae_limit,width_limit,calibration_runs,finite=True):
    reasons=[]
    if calibration_runs<10:reasons.append('insufficient_independent_calibration_runs')
    if not finite or not np.isfinite([coverage,mae,width]).all():reasons.append('non_finite_forecast')
    if coverage<.9:reasons.append('coverage_below_90_percent')
    if mae>mae_limit:reasons.append('mean_error_above_protocol_limit')
    if width>width_limit:reasons.append('interval_too_wide')
    return dict(state='可信（仅PI预测）' if not reasons else '不可信',reasons=reasons,
                optimization_allowed=False,optimization_blocker='intervention_intervals_not_independently_calibrated')
