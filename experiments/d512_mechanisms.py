"""D5.1.2: reuse frozen data; no TEP calls, no control recommendations."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.special import softmax
from causalverse.decision.mechanism import (CLASSES,NODES,STATISTICS,SmallVAR,LogisticMechanism,CandidatePolicy,
    simple_features,permitted_observations,conservative_candidates,summarize)
from causalverse.causal.dynamic import static_features,residual_features,MechanismEvidence
from causalverse.data.manifest import write_json,digest

R=Path('artifacts/d5_1_2')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def freeze():
    if (R/'protocol.json').exists():raise FileExistsError('Existing frozen protocol')
    d3=read('artifacts/d3/dataset/split_plan.json');external=[r for r in read('artifacts/d5_1_1/data_log.json')['runs'] if r['split']=='test' and r['delta']==0]
    files=[Path('artifacts/d3/dataset/split_plan.json')]
    files += list(Path('artifacts/d4').glob('*.*'))+list(Path('artifacts/d4/observations').glob('*.npz'))
    files += list(Path('artifacts/d5/uncertainty').glob('*.*'))+list(Path('artifacts/d5_1_1').glob('*.*'))
    files += [Path(r['folder'])/'trajectory.npz' for r in external]
    files += [p for p in Path('docs/research').glob('*.md') if not p.name.startswith('D5_1_2')]
    files += [p for p in Path('src').rglob('*.py') if p.name!='mechanism.py']
    write_json(R/'protected.json',{str(p):digest(p) for p in files if p.is_file()})
    write_json(R/'protocol.json',dict(d3_runs=d3['runs'],external_runs=external,windows=[180,600,1800],window_start=3600,
        dt_seconds=10,nodes=list(NODES),statistics=list(STATISTICS),models=['static','VAR','logistic'],
        logistic='multinomial linear scores; train standardization; summed CE + 0.5 L2, unpenalized intercept',
        VAR='four-node VAR lag6 ridge0.1; normal train t>=1800s only',
        static='D4 mean/log std diagonal-shrinkage signature, refit four variables',
        candidate_rule='classwise validation rank ceil((n+1)*.9); fixed close-score gap .05 expands top2; singleton must agree with ranking',
        selection='No classifier hyperparameter search; useful window chosen only by validation macro-F1, ties prefer shorter',
        external='D5.1.1 test no-action only: 20 independent paired seeds, 80 conditions; no branches counted independently',
        uncertainty='Read-only retrospective attribution of existing intervals; never resize or recalibrate',
        bootstrap=500,bootstrap_seed=512,optimization_allowed=False))
    print('D5.1.2 protocol frozen')

def load_runs(plan):
    rows=[]
    for r in plan['d3_runs']:
        p=Path('artifacts/d4/observations')/(r['dataset_run_id']+'.npz')
        with np.load(p) as d:
            assert np.array_equal(d['t_seconds'],np.arange(len(d['values']))*10)
            x=d['values'][:,[0,1,2,5]].copy()
        rows.append(dict(run_id=r['dataset_run_id'],split=r['split'],seed=r['seed'],label=r['fault_id'],values=x,source=str(p)))
    for r in plan['external_runs']:
        p=Path(r['folder'])/'trajectory.npz'
        with np.load(p) as d:x=permitted_observations(d['XMEAS'][::10],d['XMV'][::10])
        rows.append(dict(run_id=Path(r['folder']).name,split='external',seed=r['seed'],label=r['mechanism'],values=x,source=str(p)))
    assert len({r['seed'] for r in rows if r['split']=='train'})==80
    assert all(np.isfinite(r['values']).all() for r in rows)
    seedsets=[{r['seed'] for r in rows if r['split']==s} for s in ('train','validation','test','external')]
    assert all(not a&b for i,a in enumerate(seedsets) for b in seedsets[i+1:])
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');args=ap.parse_args()
    if args.freeze:freeze();return
    if (R/'metrics.json').exists():raise FileExistsError('Existing D5.1.2 evaluation')
    start=time.perf_counter();plan=read(R/'protocol.json');rows=load_runs(plan)
    var=SmallVAR().fit([r['values'][180:] for r in rows if r['split']=='train' and r['label']==0])
    np.savez_compressed(R/'VAR_model.npz',**{k:getattr(var,k) for k in ('mean','scale','coef','noise','lag','alpha')})
    records=[];metrics=[];validation=[];models={};features={}
    # Finish all training, candidate calibration and validation before any test scoring.
    for window in plan['windows']:
        for kind in plan['models']:
            groups={}
            for split in ('train','validation','test','external'):
                subset=[r for r in rows if r['split']==split];values=[]
                for r in subset:
                    x=r['values'][360:360+window//10]
                    assert len(x)==window//10
                    values.append(simple_features(x) if kind=='logistic' else static_features(x) if kind=='static' else residual_features(var,x))
                groups[split]=(subset,np.array(values),np.array([r['label'] for r in subset]))
            _,x,y=groups['train'];_,v,yv=groups['validation']
            if kind=='logistic':
                m=LogisticMechanism().fit(x,y);policy=CandidatePolicy().fit(m.scores(v),yv);scores=m.scores(v);rank,sets=policy.candidates(scores)
                params={k:getattr(m,k) for k in ('mean','scale','coef','iterations','loss')};params['thresholds']=policy.thresholds
            else:
                m=MechanismEvidence().fit(x,y).calibrate(v,yv);policy=None;d=m.distances(v);scores=softmax(-d,axis=1);rank,sets=conservative_candidates(scores,d<=m.limits)
                params={k:getattr(m,k) for k in ('center','scale','means','variances','limits')}
            np.savez_compressed(R/f'{kind}_{window}.npz',**params)
            np.savez_compressed(R/f'features_{kind}_{window}.npz',**{f'{split}_{k}':a for split,(_,a,b) in groups.items() for k,a in [('x',a),('y',b)]})
            validation.append(dict(kind=kind,window=window,**summarize(yv,rank,sets)));models[(kind,window)]=(m,policy);features[(kind,window)]=groups
    chosen={kind:min([v for v in validation if v['kind']==kind],key=lambda v:(-v['macro_f1'],v['window']))['window'] for kind in plan['models']}
    write_json(R/'validation.json',validation);write_json(R/'selection.json',dict(selected_windows=chosen,no_test_tuning=True))
    for (kind,window),(m,policy) in models.items():
        for split in ('test','external'):
            subset,x,y=features[(kind,window)][split]
            if kind=='logistic':scores=m.scores(x);rank,sets=policy.candidates(scores)
            else:
                d=m.distances(x);scores=softmax(-d,axis=1);rank,sets=conservative_candidates(scores,d<=m.limits)
            metrics.append(dict(kind=kind,window=window,split=split,**summarize(y,rank,sets)))
            for r,ranking,st,score in zip(subset,rank,sets,scores):
                candidates=[int(CLASSES[i]) for i in ranking if st[i]]
                records.append(dict(run_id=r['run_id'],seed=r['seed'],truth=r['label'],split=split,kind=kind,window=window,
                    ranking=CLASSES[ranking].tolist(),candidates=candidates,scores=score.tolist(),scores_are_calibrated_probabilities=False,
                    refused=len(candidates)!=1,status='当前观测不足以区分故障原因' if len(candidates)!=1 else '模型内单一候选，非确定因果结论',
                    reason='empty_candidate_outside_known_signature' if not candidates else 'multiple_candidates' if len(candidates)>1 else 'singleton',
                    optimization_allowed=False))
    write_json(R/'metrics.json',metrics);write_json(R/'diagnoses.json',records)
    write_json(R/'failures.json',[r for r in records if r['refused'] or r['ranking'][0]!=r['truth'] or r['truth'] not in r['candidates']])
    rng=np.random.default_rng(plan['bootstrap_seed']);comparisons=[]
    for split in ('test','external'):
        for window in plan['windows']:
            a=[r for r in records if r['split']==split and r['kind']=='logistic' and r['window']==window]
            keys=sorted({r['seed'] for r in a})
            for baseline in ('static','VAR'):
                b=[r for r in records if r['split']==split and r['kind']==baseline and r['window']==window]
                byid={r['run_id']:r for r in b};differences=[]
                for seed in keys:
                    same=[r for r in a if r['seed']==seed]
                    differences.append(np.mean([int(r['ranking'][0]==r['truth'])-int(byid[r['run_id']]['ranking'][0]==r['truth']) for r in same]))
                ci=np.quantile([rng.choice(differences,len(keys)).mean() for _ in range(500)],[.025,.975])
                comparisons.append(dict(split=split,window=window,baseline=baseline,independent_seed_groups=len(keys),
                    top1_difference=float(np.mean(differences)),seed_bootstrap95=ci.tolist()))
    write_json(R/'comparisons.json',comparisons)
    write_json(R/'audit.json',dict(historical_inputs_and_reports_unchanged=all(digest(p)==h for p,h in read(R/'protected.json').items()),
        new_simulations=0,d3_runs=200,external_seed_groups=20,external_conditions=80,elapsed_seconds=time.perf_counter()-start))
    print('D5.1.2 evaluation complete')
if __name__=='__main__':main()
