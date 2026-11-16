import json,time,copy
from pathlib import Path
import numpy as np
from causalverse.decision.intervention_model import ConditionalPredictor
from causalverse.decision.intervention_calibration import calibrate,intervals
from causalverse.decision.action_support import ActionSupport
from causalverse.decision.uncertainty import MechanismEnsemble,evaluate_all_mechanisms
from causalverse.causal.dynamic import DynamicModel
from causalverse.data.manifest import write_json,digest

R=Path('artifacts/d5_1_1');H=np.array([10,30,60,120,300,600]);S=np.array([.25,.5,5.])
def main():
    if (R/'metrics.json').exists():raise FileExistsError('Existing results')
    plan=json.loads((R/'protocol.json').read_text());log=json.loads((R/'data_log.json').read_text());rows=[]
    assert len(log['runs'])==720
    for rec in log['runs']:
        p=R/'observed'/(Path(rec['folder']).name+'.npz')
        with np.load(p) as d:rows.append(dict(**rec,history=d['history'].copy(),truth=d['values'][H,:3],delta_truth=d['delta_values'][H,:3]))
    groups={s:sorted([r for r in rows if r['split']==s],key=lambda r:(r['seed'],r['mechanism'],r['delta'])) for s in plan['seeds']}
    train=groups['train'];support=ActionSupport().fit([r['history'] for r in train]);np.savez(R/'support.npz',lower=support.lower,upper=support.upper,scale=support.scale)
    models={};rng=np.random.default_rng(plan['bootstrap_seed'])
    for kind in ('action','delta'):
        members=[];ids_all=[]
        for i in range(20):
            ids=rng.choice(plan['seeds']['train'],20,replace=True);sample=[r for seed in ids for r in train if r['seed']==seed]
            members.append(ConditionalPredictor(kind).fit(sample));ids_all.append(ids)
        models[kind]=members
        params={}
        for k,m in enumerate(members):
            for name in ('model','base'):
                if not hasattr(m,name):continue
                obj=getattr(m,name)
                for field in ('mean','scale','coef'):params[f'{k}_{name}_{field}']=getattr(obj,field)
        np.savez_compressed(R/f'{kind}_ensemble.npz',bootstrap_seeds=ids_all,**params)
    pi=[];stable=[];spectral=[]
    for c in (0,4,11,14):
        p=np.load(f'artifacts/d5/uncertainty/ensemble_m{c}.npz');e=MechanismEnsemble();e.models=[];e.banks=list(p['residual_banks'])
        for coef,mean,scale in zip(p['coef'],p['mean'],p['scale']):
            m=DynamicModel(6,.1,True);m.coef=coef.copy();m.mean=mean;m.scale=scale;e.models.append(m)
        es=copy.deepcopy(e)
        for k,m in enumerate(es.models):
            old=m.coef.copy();factor=np.maximum(1,np.sum(np.abs(m.coef[1:]),axis=0)/.995);m.coef[1:]/=factor
            A=np.zeros((42,42));A[:7]=m.coef[1:].T;A[7:,:-7]=np.eye(35)
            B=A.copy();B[:7]=old[1:].T
            spectral.append(dict(mechanism=c,member=k,original=float(max(abs(np.linalg.eigvals(B)))),projected=float(max(abs(np.linalg.eigvals(A))))))
        pi.append(e);stable.append(es)
    write_json(R/'stability_projection.json',spectral)
    np.savez_compressed(R/'stable_projection.npz',coefficients=np.array([[m.coef for m in e.models] for e in stable]))
    predictions={};metrics=[];failed=[];calibrations={}
    for kind in ('action','delta','PI','PI_stable'):
        result={}
        for split in ('calibration','test'):
            pred=[];disagree=[]
            for n,r in enumerate(groups[split]):
                if kind in models:
                    v=np.array([m.predict(r['history'],r['delta'],r['command_before']) for m in models[kind]]);point=v.mean(0);std=v.std(0)
                else:
                    override=dict(value=r['command_before']+r['delta'],duration_seconds=120) if r['delta'] else None
                    ensemble=pi if kind=='PI' else stable
                    warm=evaluate_all_mechanisms(ensemble,r['history'],1,69001)['mean'][0]
                    warm[5]=r['command_before']
                    f=evaluate_all_mechanisms(ensemble,np.vstack([r['history'],warm]),60,69001,override)
                    point=f['mean'][H//10-1,:3];std=f['parameter_std'][:,H//10-1,:3].mean(0)
                pred.append(point);disagree.append(float(np.max(std/S)))
            result[split]=np.array(pred)
            np.savez_compressed(R/f'predictions_{kind}_{split}.npz',predicted=pred,truth=[r['truth'] for r in groups[split]],disagreement=disagree)
            if split=='calibration':
                errors=(np.array([r['truth'] for r in groups[split]])-pred).reshape(20,4,3,6,3)
                q,qa=calibrate(errors,S);calibrations[kind]=dict(joint=q,actionwise=qa.tolist())
                # Calibrated before evaluation; no test fitting or threshold adaptation.
                write_json(R/f'calibration_{kind}.json',calibrations[kind])
        pred=result['test'].reshape(20,4,3,6,3);truth=np.array([r['truth'] for r in groups['test']]).reshape(20,4,3,6,3)
        q=calibrations[kind]['joint'];qa=np.array(calibrations[kind]['actionwise'])
        for ai,delta in enumerate((0,1,5)):
            joint=np.abs(pred-truth)<=q*S;separate=np.abs(pred[:,:,ai]-truth[:,:,ai])<=qa[ai]*S
            for mi,mechanism in enumerate((0,4,11,14)):
                mae=np.abs(pred[:,mi,ai]-truth[:,mi,ai]).mean(axis=(0,1))
                covered=joint[:,mi,ai].all(axis=(1,2));marginal=joint[:,mi,ai].mean(axis=0)
                metrics.append(dict(kind=kind,mechanism=mechanism,delta=delta,MAE=mae.tolist(),joint_width=(2*q*S).tolist(),
                    MAE_by_horizon=np.abs(pred[:,mi,ai]-truth[:,mi,ai]).mean(axis=0).tolist(),
                    action_width=(2*qa[ai]*S).tolist(),run_action_coverage=float(covered.mean()),
                    actionwise_coverage=float(separate[:,mi].all(axis=(1,2)).mean()),cell_coverage=marginal.tolist(),
                    optimization_allowed=False))
                for i in range(20):
                    if not covered[i]:failed.append(dict(kind=kind,seed=plan['seeds']['test'][i],mechanism=mechanism,delta=delta,errors=(pred[i,mi,ai]-truth[i,mi,ai]).tolist()))
        all_cover=(np.abs(pred-truth)<=q*S).all(axis=(1,2,3,4))
        np.savez(R/f'joint_{kind}.npz',covered=all_cover)
    write_json(R/'metrics.json',metrics);write_json(R/'calibration.json',calibrations);write_json(R/'failures.json',failed)
    # Every step of every node is checked. Controlled artificial shifts test OOD detection.
    support_rows=[]
    disagreement_values={k:np.load(R/f'predictions_{k}_test.npz')['disagreement'] for k in ('action','delta','PI','PI_stable')}
    for index,r in enumerate(groups['test']):
        checks={}
        for name,h,delta,duration,horizon in [('in_domain',r['history'],r['delta'],120,600),('hidden_early_spike',r['history'].copy(),r['delta'],120,600),('large_action',r['history'],10,120,600),('long_duration',r['history'],r['delta'],300,600),('long_horizon',r['history'],r['delta'],120,900)]:
            if name=='hidden_early_spike':h[0,0]+=1e6
            checks[name]=support.check(h,delta,duration,horizon,0,command=r['command_before'])
        checks['by_model']={k:support.check(r['history'],r['delta'],120,600,float(values[index]),
            radius=None if k in ('action','delta') else max(s['original' if k=='PI' else 'projected'] for s in spectral),command=r['command_before']) for k,values in disagreement_values.items()}
        support_rows.append(dict(seed=r['seed'],mechanism=r['mechanism'],delta=r['delta'],checks=checks))
    write_json(R/'support_results.json',support_rows)
    write_json(R/'historical_protection.json',dict(unchanged=all(digest(p)==h for p,h in json.loads((R/'protected.json').read_text()).items())))
    print('Independent intervention analysis complete')
if __name__=='__main__':main()
