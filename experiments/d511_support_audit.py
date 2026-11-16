"""Conservative supplementary candidate-disagreement and actuator audit.

Added after primary test evaluation; cannot grant or loosen authorization.
Candidate fits use training observations only, never the current true IDV.
"""
import json
from pathlib import Path
import numpy as np
from causalverse.decision.intervention_model import ConditionalPredictor
from causalverse.decision.action_support import candidate_disagreement
from causalverse.decision.uncertainty import MechanismEnsemble,evaluate_all_mechanisms
from causalverse.causal.dynamic import DynamicModel
from causalverse.data.manifest import write_json

R=Path('artifacts/d5_1_1');S=np.array([.25,.5,5.]);H=np.array([10,30,60,120,300,600])
def main():
    if (R/'candidate_disagreement.json').exists():raise FileExistsError('Audit already exists')
    log=json.loads((R/'data_log.json').read_text())['runs'];rows=[]
    for r in sorted(log,key=lambda r:(r['seed'],r['mechanism'],r['delta'])):
        with np.load(R/'observed'/(Path(r['folder']).name+'.npz')) as d:
            rows.append(dict(**r,history=d['history'].copy(),truth=d['values'][H,:3],delta_truth=d['delta_values'][H,:3]))
    test=[r for r in rows if r['split']=='test'];train=[r for r in rows if r['split']=='train']
    plan=json.loads((R/'protocol.json').read_text());rng=np.random.default_rng(640002);candidate={}
    params={}
    for kind in ('action','delta'):
        candidate[kind]=[]
        for mechanism in (0,4,11,14):
            members=[]
            for j in range(20):
                seeds=rng.choice(plan['seeds']['train'],20,replace=True)
                sample=[r for seed in seeds for r in train if r['seed']==seed and r['mechanism']==mechanism]
                m=ConditionalPredictor(kind).fit(sample);members.append(m)
                params[f'{kind}_{mechanism}_{j}_seeds']=seeds
                for name in ('model','base'):
                    if hasattr(m,name):
                        for field in ('mean','scale','coef'):params[f'{kind}_{mechanism}_{j}_{name}_{field}']=getattr(getattr(m,name),field)
            candidate[kind].append(members)
    np.savez_compressed(R/'candidate_support_ensembles.npz',**params)
    for kind in ('PI','PI_stable'):
        candidate[kind]=[]
        for c in (0,4,11,14):
            p=np.load(f'artifacts/d5/uncertainty/ensemble_m{c}.npz');e=MechanismEnsemble();e.models=[];e.banks=list(p['residual_banks'])
            for coef,mean,scale in zip(p['coef'],p['mean'],p['scale']):
                m=DynamicModel(6,.1,True);m.coef=coef.copy();m.mean=mean;m.scale=scale
                if kind=='PI_stable':m.coef[1:]/=np.maximum(1,np.sum(np.abs(m.coef[1:]),axis=0)/.995)
                e.models.append(m)
            candidate[kind].append(e)
    checks=json.loads((R/'support_results.json').read_text());result=[];actuators=[]
    for i,r in enumerate(test):
        item=dict(seed=r['seed'],mechanism=r['mechanism'],delta=r['delta'],models={})
        for kind,models in candidate.items():
            if kind in ('action','delta'):
                means=np.array([[m.predict(r['history'],r['delta'],r['command_before']) for m in members] for members in models]).mean(1)
            else:
                warm=evaluate_all_mechanisms(models,r['history'],1,69001)['mean'][0];warm[5]=r['command_before']
                override=dict(value=r['command_before']+r['delta'],duration_seconds=120) if r['delta'] else None
                means=evaluate_all_mechanisms(models,np.vstack([r['history'],warm]),60,69001,override)['mechanism_means'][:,H//10-1,:3]
            disagreement=candidate_disagreement(means,S)
            old=checks[i]['checks']['by_model'][kind];reasons=list(old['reasons'])
            if disagreement>1:reasons.append('candidate_mechanism_disagreement')
            item['models'][kind]=dict(candidate_means=means.tolist(),normalized_range=disagreement,supported=not reasons,reasons=reasons)
        result.append(item)
        with np.load(Path(r['folder'])/'trajectory.npz') as d:
            ix=5400+np.array([0,119,120,300,600]);actuators.append(dict(seed=r['seed'],mechanism=r['mechanism'],delta=r['delta'],
                offsets=[0,119,120,300,600],command=d['XMV'][ix,9].tolist(),accepted_target=d['valve_target'][ix,9].tolist(),
                actual_position=d['valve_position'][ix,9].tolist(),paired_effects=r['delta_truth'].tolist()))
    write_json(R/'candidate_disagreement.json',dict(post_test_conservative_audit=True,rows=result))
    write_json(R/'actuator_audit.json',actuators)
    print('Candidate disagreement and offline actuator audit complete')
if __name__=='__main__':main()
