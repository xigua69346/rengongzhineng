import json
from pathlib import Path
import numpy as np
from scipy.stats import f as f_dist
from causalverse.causal.dynamic import *
from causalverse.data.manifest import write_json,digest

ROOT=Path('artifacts/d4');D3=Path('artifacts/d3/dataset')

def feature(kind,model,x):return static_features(x) if kind=='static' else residual_features(model,x)

def summarize(labels,rank,sets):
    classes=np.array([0,4,11,14]);truth=np.array(labels);pred=classes[rank[:,0]]
    cm=np.zeros((4,4),int)
    for y,p in zip(truth,pred):cm[list(classes).index(y),list(classes).index(p)]+=1
    certain=sets.sum(1)==1;chosen=classes[np.argmax(sets,axis=1)];fault=truth!=0
    return dict(top1=float(np.mean(pred==truth)),top3=float(np.mean([y in classes[r[:3]] for y,r in zip(truth,rank)])),
      root_top1_fault_only=float(np.mean(pred[fault]==truth[fault])),
      root_top3_note='Three known fault mechanisms only: listing all three is tautologically 100%; overall top3 includes normal class',
      diagnosis_coverage=float(certain.mean()),refusal_ratio=float((~certain).mean()),
      candidate_set_coverage=float(np.mean([s[list(classes).index(y)] for y,s in zip(truth,sets)])),
      wrong_certain_rate_all_runs=float(np.mean(certain&(chosen!=truth))),
      wrong_certain_rate_given_certain=float(np.mean(chosen[certain]!=truth[certain])) if certain.any() else None,
      confusion_matrix=cm.tolist(),per_fault={str(c):dict(n=int(np.sum(truth==c)),top1=float(np.mean(pred[truth==c]==c)),
            rejection=float(np.mean(~certain[truth==c]))) for c in classes})

def main():
    if (ROOT/'test_diagnoses.json').exists():raise FileExistsError('Existing D4 evaluation')
    plan=json.loads((D3/'split_plan.json').read_text());protocol=json.loads((ROOT/'protocol.json').read_text());runs=[]
    (ROOT/'observations').mkdir(exist_ok=True)
    for s in plan['runs']:
        with np.load(D3/'raw'/s['dataset_run_id']/'trajectory.npz') as raw:
            x=observed(raw['XMEAS'][::10],raw['XMV'][::10])
        np.savez_compressed(ROOT/'observations'/f"{s['dataset_run_id']}.npz",values=x,t_seconds=np.arange(len(x))*10)
        runs.append((s,x))
    normal_train=[x[180:] for s,x in runs if s['split']=='train' and s['fault_id']==0]
    normal_val=[x[180:] for s,x in runs if s['split']=='validation' and s['fault_id']==0]
    models={};selections=[]
    for kind,constrained in [('VAR',False),('SCM',True)]:
        best=None
        for lag in protocol['lags']:
            for alpha in protocol['ridge']:
                m=DynamicModel(lag,alpha,constrained).fit(normal_train)
                mse=float(np.mean([np.mean((m.residuals(x)*m.noise)**2) for x in normal_val]))
                selections.append(dict(kind=kind,lag=lag,alpha=alpha,validation_mse=mse))
                if best is None or mse<best[0]:best=(mse,m)
        models[kind]=best[1]
        m=best[1];np.savez(ROOT/f'{kind}_model.npz',coef=m.coef,mean=m.mean,scale=m.scale,noise=m.noise,lag=m.lag,alpha=m.alpha)
    write_json(ROOT/'model_selection.json',selections)
    stability=[]
    for x in normal_train:
        m=DynamicModel(models['SCM'].lag,models['SCM'].alpha,True).fit([x]);stability.append(m.coef)
    np.savez(ROOT/'parameter_stability.npz',per_run_coefficients=stability,pooled=models['SCM'].coef)
    # Candidate predictive links from per-run OLS; p-values are exploratory under autocorrelation.
    lag=models['VAR'].lag;edge=[]
    for source in range(7):
        for target in range(7):
            if source==target:continue
            pvalues=[];improvements=[]
            for x in normal_train:
                z=(x-models['VAR'].mean)/models['VAR'].scale;X=design(z,lag);y=z[lag:,target]
                full=np.linalg.lstsq(X,y,rcond=None)[0];rss=np.sum((y-X@full)**2)
                keep=[i for i in range(X.shape[1]) if i not in [1+k*7+source for k in range(lag)]]
                A=X[:,keep];rss0=np.sum((y-A@np.linalg.lstsq(A,y,rcond=None)[0])**2)
                statistic=max(0,(rss0-rss)/lag/(rss/max(1,len(y)-X.shape[1])))
                pvalues.append(float(f_dist.sf(statistic,lag,len(y)-X.shape[1])))
                improvements.append(float((rss0-rss)/max(rss0,1e-12)))
            edge.append(dict(source=NAMES[source],target=NAMES[target],p_median=float(np.median(pvalues)),fraction_p_below_05=float(np.mean(np.array(pvalues)<.05)),predictive_gain_median=float(np.median(improvements)),process_prior=source in PARENTS[target]))
    # BH correction to median per-run p summaries: heuristic, not a calibrated familywise claim.
    order=np.argsort([e['p_median'] for e in edge]);cut=0
    for k,i in enumerate(order,1):
        if edge[i]['p_median']<=.05*k/len(edge):cut=k
    chosen=set(order[:cut]);
    for i,e in enumerate(edge):e['exploratory_selected']=i in chosen
    write_json(ROOT/'discovered_edges.json',edge)
    write_json(ROOT/'static_correlations.json',dict(nodes=NAMES,normal_train=np.corrcoef(np.concatenate(normal_train).T).tolist()))
    records=[];evaluations=[];frozen=[]
    for window in protocol['windows_seconds']:
        for kind in ('static','VAR','SCM'):
            m=models.get(kind);groups={}
            for split in ('train','validation','test'):
                # All runs diagnosed at the same fixed experiment clock. No IDV channel is read.
                subset=[(s,x[360:360+window//10]) for s,x in runs if s['split']==split]
                groups[split]=(subset,np.array([feature(kind,m,x) for s,x in subset]),np.array([s['fault_id'] for s,x in subset]))
            a,train,y=groups['train'];b,val,yv=groups['validation']
            evidence=MechanismEvidence().fit(train,y).calibrate(val,yv)
            np.savez(ROOT/f'evidence_{kind}_{window}.npz',center=evidence.center,scale=evidence.scale,means=evidence.means,variances=evidence.variances,limits=evidence.limits)
            frozen.append(dict(kind=kind,window=window,limits=evidence.limits.tolist(),classes=[0,4,11,14]))
            subset,test,truth=groups['test'];rank,sets,d=evidence.diagnose(test)
            ev=summarize(truth,rank,sets);evaluations.append(dict(kind=kind,window=window,**ev))
            for (s,x),r,st,dist in zip(subset,rank,sets,d):
                cand=np.array([0,4,11,14])[st].tolist()
                records.append(dict(run_id=s['dataset_run_id'],seed=s['seed'],truth=s['fault_id'],kind=kind,window=window,
                                    ranking=np.array([0,4,11,14])[r].tolist(),candidate_mechanisms=cand,
                                    certain=len(cand)==1,status='certain_within_model' if len(cand)==1 else '当前观测不足以确定根因',distances=dist.tolist()))
    write_json(ROOT/'evidence_calibration.json',frozen);write_json(ROOT/'test_diagnoses.json',records);write_json(ROOT/'diagnosis_metrics.json',evaluations)
    write_json(ROOT/'failure_cases.json',[r for r in records if r['ranking'][0]!=r['truth'] or not r['certain'] or r['truth'] not in r['candidate_mechanisms']])
    # Paired bootstrap over complete D3 test runs; no second-wise resampling.
    rng=np.random.default_rng(19);ci=[]
    for window in protocol['windows_seconds']:
        rs={k:[r for r in records if r['kind']==k and r['window']==window] for k in ('static','VAR','SCM')}
        for baseline in ('static','VAR'):
            delta=np.array([int(a['ranking'][0]==a['truth'])-int(b['ranking'][0]==b['truth']) for a,b in zip(rs['SCM'],rs[baseline])])
            samples=[np.mean(rng.choice(delta,len(delta),replace=True)) for _ in range(500)]
            ci.append(dict(window=window,baseline=baseline,mean_difference=float(delta.mean()),bootstrap95=np.quantile(samples,[.025,.975]).tolist()))
    write_json(ROOT/'paired_bootstrap.json',ci)
    print('D4 observation models and diagnoses complete')

if __name__=='__main__':main()
