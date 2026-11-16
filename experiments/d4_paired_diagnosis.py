from pathlib import Path
import json,numpy as np
from causalverse.causal.dynamic import *
from causalverse.data.manifest import write_json
from d4_models import summarize

root=Path('artifacts/d4');logs=json.loads((root/'pair_log.json').read_text());metrics=[];results=[]
for kind in ('static','VAR','SCM'):
    if kind!='static':
        p=np.load(root/f'{kind}_model.npz');m=DynamicModel(int(p['lag']),float(p['alpha']),kind=='SCM')
        for k in ('mean','scale','coef','noise'):setattr(m,k,p[k])
    groups={}
    for split in ('train','validation','test'):
        rows=[r for r in logs if r['split']==split and r['delta']==0];features=[]
        for r in rows:
            with np.load(Path(r['folder'])/'trajectory.npz') as d:x=observed(d['XMEAS'][3600:6000:10],d['XMV'][3600:6000:10])
            features.append(static_features(x) if kind=='static' else residual_features(m,x))
        groups[split]=(rows,np.array(features),np.array([r['fault_id'] for r in rows]))
    _,x,y=groups['train'];_,v,yv=groups['validation'];e=MechanismEvidence().fit(x,y).calibrate(v,yv)
    rows,t,yt=groups['test'];ranking,sets,d=e.diagnose(t);metrics.append(dict(kind=kind,**summarize(yt,ranking,sets)))
    for r,rank,st in zip(rows,ranking,sets):results.append(dict(seed=r['seed'],truth=r['fault_id'],kind=kind,ranking=np.array([0,4,11,14])[rank].tolist(),candidates=np.array([0,4,11,14])[st].tolist()))
write_json(root/'paired_passive_metrics.json',metrics);write_json(root/'paired_passive_diagnoses.json',results)
# Bootstrap complete seeds, keeping fault conditions and action doses together.
effects=json.loads((root/'intervention_aligned/intervention_effects.json').read_text());rng=np.random.default_rng(19);intervals=[]
for target in NAMES[:3]:
    per_seed=[np.mean([abs(r['error']) for r in effects if r['split']=='test' and r['target']==target and r['seed']==seed]) for seed in range(430000,430005)]
    boot=[np.mean(rng.choice(per_seed,5,replace=True)) for _ in range(500)]
    intervals.append(dict(target=target,seed_level_MAE=per_seed,bootstrap95=np.quantile(boot,[.025,.975]).tolist(),independent_seeds=5))
write_json(root/'intervention_aligned/effect_seed_bootstrap.json',intervals)
