import json
from pathlib import Path
import numpy as np
from causalverse.causal.dynamic import *
from causalverse.data.manifest import write_json
from d4_models import summarize

ROOT=Path('artifacts/d4')
OUT=ROOT/'intervention_aligned'
def read(folder):
    with np.load(Path(folder)/'trajectory.npz') as d:
        return observed(d['XMEAS'],d['XMV']),d['rng_state'].copy(),d['coolant_inlet_temperature'].copy()

def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'intervention_metrics.json').exists():raise FileExistsError('Existing intervention results')
    logs=json.loads((ROOT/'pair_log.json').read_text());pairs={};effects=[];evidence=[];cross=[]
    par=np.load(ROOT/'SCM_model.npz');model=DynamicModel(int(par['lag']),float(par['alpha']),True)
    for k in ('mean','scale','coef','noise'):setattr(model,k,par[k])
    for r in logs:pairs.setdefault((r['split'],r['seed'],r['fault_id']),{})[r['delta']]=r
    for (split,seed,fid),arms in pairs.items():
        base,rb,inlet=read(arms[0]['folder']);features=[]
        # Compare fault and normal arms from exactly the same pre-fault history.
        normal=next(r for r in logs if r['seed']==seed and r['fault_id']==0 and r['delta']==0)
        _,normal_rng,_=read(normal['folder'])
        cross.append(dict(seed=seed,fault_id=fid,rng_equal_to_normal=bool(np.array_equal(rb,normal_rng))))
        for delta in (1,5):
            action,ra,ia=read(arms[delta]['folder']);actual=(action-base)[5410:6000:10,:3]
            hist=base[:5401:10].copy();action_history=hist.copy()
            action_history[-1,5]=base[5399,5]+delta
            predicted=model.rollout(action_history,59,dict(steps=11,value=float(base[5399,5]+delta)))[:,:3]-model.rollout(hist,59)[:,:3]
            early=(action-base)[5460:5520,:3].mean(0);late=(action-base)[5700:6000,:3].mean(0)
            features.extend([*early,*late])
            for j,name in enumerate(NAMES[:3]):
                a=float(actual[:,j].mean());p=float(predicted[:,j].mean())
                effects.append(dict(split=split,seed=seed,fault_id=fid,delta=delta,target=name,
                    actual_mean_effect=a,predicted_mean_effect=p,error=p-a,trajectory_rmse=float(np.sqrt(np.mean((predicted[:,j]-actual[:,j])**2))),
                    actual_peak_lag_seconds=int(np.argmax(np.abs(actual[:,j]))*10+10),
                    predicted_peak_lag_seconds=int(np.argmax(np.abs(predicted[:,j]))*10+10),
                    direction_correct=bool(np.sign(a)==np.sign(p)) if abs(a)>1e-8 else None,
                    paired_rng=bool(np.array_equal(rb,ra)),paired_inlet=bool(np.array_equal(inlet,ia))))
            np.savez(OUT/f'effect_{seed}_{fid}_{delta}.npz',actual=actual,predicted=predicted,t_seconds=np.arange(10,600,10))
        evidence.append(dict(split=split,seed=seed,fault_id=fid,features=features))
    train=[r for r in evidence if r['split']=='train'];val=[r for r in evidence if r['split']=='validation'];test=[r for r in evidence if r['split']=='test']
    ev=MechanismEvidence().fit(np.array([r['features'] for r in train]),np.array([r['fault_id'] for r in train])).calibrate(np.array([r['features'] for r in val]),np.array([r['fault_id'] for r in val]))
    np.savez(OUT/'intervention_evidence.npz',center=ev.center,scale=ev.scale,means=ev.means,variances=ev.variances,limits=ev.limits)
    rank,sets,d=ev.diagnose(np.array([r['features'] for r in test]))
    metric=summarize([r['fault_id'] for r in test],rank,sets)
    diagnoses=[]
    for r,ranking,st in zip(test,rank,sets):
        diagnoses.append(dict(seed=r['seed'],truth=r['fault_id'],ranking=np.array([0,4,11,14])[ranking].tolist(),candidates=np.array([0,4,11,14])[st].tolist(),status='当前观测不足以确定根因' if st.sum()!=1 else 'certain_within_model'))
    write_json(OUT/'intervention_metrics.json',metric);write_json(OUT/'intervention_diagnoses.json',diagnoses)
    write_json(OUT/'intervention_effects.json',effects);write_json(OUT/'cross_fault_pairing.json',cross)
    write_json(OUT/'intervention_failures.json',[r for r in effects if r['split']=='test' and (not r['paired_rng'] or r['direction_correct'] is False or abs(r['error'])>.1)])
    summary=[]
    for target in NAMES[:3]:
        rows=[r for r in effects if r['split']=='test' and r['target']==target];valid=[r for r in rows if r['direction_correct'] is not None]
        summary.append(dict(target=target,n=len(rows),mean_absolute_effect_error=float(np.mean([abs(r['error']) for r in rows])),
            direction_accuracy=float(np.mean([r['direction_correct'] for r in valid])) if valid else None,
            all_rng_paired=all(r['paired_rng'] for r in rows),all_inlet_paired=all(r['paired_inlet'] for r in rows)))
    write_json(OUT/'effect_summary.json',summary);print('Paired effect and mechanism validation complete')

if __name__=='__main__':main()
