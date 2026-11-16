"""D5.1 only. Never runs an optimizer or changes D2/D3/D4 artifacts."""
import argparse,json,time
from pathlib import Path
import numpy as np
from causalverse.causal.dynamic import observed
from causalverse.decision.uncertainty import *
from causalverse.data.manifest import write_json,digest

ROOT=Path('artifacts/d5/uncertainty');D4=Path('artifacts/d4')

def freeze():
    if (ROOT/'protocol.json').exists():raise FileExistsError('Frozen D5.1 protocol already exists')
    ROOT.mkdir(parents=True,exist_ok=True)
    protected=[]
    for base in ('artifacts/d2','artifacts/d3','artifacts/d4'):
        protected.extend(p for p in Path(base).rglob('*') if p.is_file())
    protected.extend(Path('src/causalverse/simulation').glob('*.py'));protected.extend(Path('src/causalverse/causal').glob('*.py'))
    write_json(ROOT/'protected_before.json',{str(p):digest(p) for p in protected})
    plan=json.loads(Path('artifacts/d3/dataset/split_plan.json').read_text())
    write_json(ROOT/'protocol.json',dict(stage='D5.1 only',mechanisms=[0,4,11,14],members=20,lag=6,alpha=.1,
       origins_seconds=[3600,5400,9000],horizons_seconds=[10,30,60,120,300,600],block_steps=12,
       process_replicas_per_member=2,coverage=.9,bootstrap_seed=51001,prediction_seed=52001,
       mae_limits=[.25,.5,5.],mean_width_limits=[1.,2.,20.],threshold_units=['degC','degC','kPa'],
       threshold_interpretation='predeclared research accuracy/utility tolerances; NOT industrial safety limits',
       calibration='one max-over-three-origins score per independent validation run; classwise quantile, worst across all four classes',
       no_test_tuning=True,source_plan_sha256=digest('artifacts/d3/dataset/split_plan.json'),runs=plan['runs'],
       intervention_gate='PI forecast credibility does not authorize optimization; D4 intervention validation has only three seeds per class',
       reuse_note='Existing D3 split, training-independent test but previously examined in D3/D4; retrospective staged research, not fresh blind trial'))

def main():
    if (ROOT/'metrics.json').exists() or (ROOT/'ensemble_m0.npz').exists():
        raise FileExistsError('Existing complete or partial D5.1 results; archive before rerun')
    p=json.loads((ROOT/'protocol.json').read_text());start=time.perf_counter();runs=[]
    for s in p['runs']:
        with np.load(D4/'observations'/f"{s['dataset_run_id']}.npz") as d:runs.append((s,d['values'].copy()))
    ensembles=[];metadata=[]
    for c in p['mechanisms']:
        rr=[x[(180 if c==0 else 360):] for s,x in runs if s['split']=='train' and s['fault_id']==c]
        e=MechanismEnsemble(p['members'],p['lag'],p['alpha'],p['block_steps']).fit(rr,p['bootstrap_seed']+c)
        e.save(ROOT/f'ensemble_m{c}.npz');ensembles.append(e)
        metadata.append(dict(mechanism=c,fit_runs=[s['dataset_run_id'] for s,x in runs if s['split']=='train' and s['fault_id']==c],members=len(e.models)))
        print('ensemble fitted',c,flush=True)
    write_json(ROOT/'ensemble_manifest.json',metadata)
    horizons=np.array(p['horizons_seconds'])//10-1;origins=np.array(p['origins_seconds'])//10
    # Stochastic forecast seeds depend on frozen row order, never observed outcomes.
    def predict(split):
        output=[]
        folder=ROOT/split;folder.mkdir(exist_ok=True)
        for i,(s,x) in enumerate((v for v in runs if v[0]['split']==split)):
            predictions=[];support=[]
            for k,o in enumerate(origins):
                h=x[:o+1];r=evaluate_all_mechanisms(ensembles,h,60,p['prediction_seed']+i*100+k)
                predictions.append(r);support.append(support_check(ensembles,h))
            data={key:np.array([r[key][horizons,:3] for r in predictions]) for key in ('lower','upper','mean')}
            data.update(truth=np.array([x[o+horizons+1,:3] for o in origins]),
              mechanism_means=np.array([r['mechanism_means'][:,horizons,:3] for r in predictions]),
              parameter_std=np.array([r['parameter_std'][:,horizons,:3] for r in predictions]),
              total_std=np.array([r['total_std'][:,horizons,:3] for r in predictions]))
            np.savez_compressed(folder/f"{s['dataset_run_id']}.npz",**data)
            output.append((s,data,support));print('prediction',split,s['dataset_run_id'],flush=True)
        return output
    validation=predict('validation')
    class_q=[]
    for c in p['mechanisms']:
        scores=[np.maximum(np.maximum(d['lower']-d['truth'],d['truth']-d['upper']),0).max(axis=0) for s,d,sup in validation if s['fault_id']==c]
        class_q.append(conformal_radius(scores,p['coverage']))
    q=np.max(class_q,axis=0)
    np.savez(ROOT/'calibration.npz',q=q,class_q=class_q)
    write_json(ROOT/'calibration_manifest.json',dict(run_ids=[s['dataset_run_id'] for s,d,sup in validation],
               runs_per_mechanism=10,score_unit='one whole run, maximum over three fixed origins',radii=q.tolist()))
    # Freeze validation gates before producing or evaluating D5.1 test forecasts.
    gates=[]
    for h,seconds in enumerate(p['horizons_seconds']):
        for j,name in enumerate(['T9','C21','P7']):
            worst_coverage=1.;worst_mae=0.;worst_width=0.
            for c in p['mechanisms']:
                ds=[d for s,d,sup in validation if s['fault_id']==c]
                cover=np.mean([np.all((d['truth'][:,h,j]>=d['lower'][:,h,j]-q[h,j])&(d['truth'][:,h,j]<=d['upper'][:,h,j]+q[h,j])) for d in ds])
                worst_coverage=min(worst_coverage,float(cover))
                worst_mae=max(worst_mae,float(np.mean([np.abs(d['mean'][:,h,j]-d['truth'][:,h,j]).mean() for d in ds])))
                worst_width=max(worst_width,float(np.mean([(d['upper'][:,h,j]-d['lower'][:,h,j]+2*q[h,j]).mean() for d in ds])))
            gate=trust_state(worst_coverage,worst_mae,worst_width,p['mae_limits'][j],p['mean_width_limits'][j],10)
            gates.append(dict(target=name,horizon_seconds=seconds,validation_worst_coverage=worst_coverage,validation_worst_mae=worst_mae,validation_worst_mean_width=worst_width,**gate))
    write_json(ROOT/'validation_gates.json',gates)
    test=predict('test');metrics=[];failed=[]
    for c in p['mechanisms']:
        for h,seconds in enumerate(p['horizons_seconds']):
            for j,name in enumerate(['T9','C21','P7']):
                rows=[(s,d,sup) for s,d,sup in test if s['fault_id']==c]
                included=[];width=[];errors=[];pstd=[];tstd=[];disagreement=[]
                for s,d,sup in rows:
                    lo=d['lower'][:,h,j]-q[h,j];hi=d['upper'][:,h,j]+q[h,j];truth=d['truth'][:,h,j]
                    inc=(truth>=lo)&(truth<=hi);included.append(inc);width.append(hi-lo);errors.append(np.abs(d['mean'][:,h,j]-truth))
                    pstd.append(d['parameter_std'][:,:,h,j].mean());tstd.append(d['total_std'][:,:,h,j].mean());disagreement.append(np.ptp(d['mechanism_means'][:,:,h,j],axis=1).mean())
                    if not inc.all() or not all(x['supported'] for x in sup):failed.append(dict(run_id=s['dataset_run_id'],mechanism_truth=c,target=name,horizon_seconds=seconds,covered_origins=inc.tolist(),support=sup))
                run_cover=np.array([bool(np.all(a)) for a in included]);rng=np.random.default_rng(55101+c+h*100+j)
                boot=[np.mean(rng.choice(run_cover,len(run_cover),replace=True)) for _ in range(500)]
                metrics.append(dict(mechanism_truth=c,target=name,horizon_seconds=seconds,independent_runs=len(rows),
                   run_simultaneous_coverage=float(run_cover.mean()),origin_marginal_coverage=float(np.mean(included)),
                   mean_width=float(np.mean(width)),mean_absolute_error=float(np.mean(errors)),coverage_bootstrap95=np.quantile(boot,[.025,.975]).tolist(),
                   parameter_std=float(np.mean(pstd)),total_std=float(np.mean(tstd)),mechanism_mean_range=float(np.mean(disagreement))))
    write_json(ROOT/'metrics.json',metrics);write_json(ROOT/'failure_cases.json',failed)
    write_json(ROOT/'execution.json',dict(elapsed_seconds=time.perf_counter()-start,ensemble_members=80,validation_runs=40,test_runs=80,origins_per_run=3,synthetic_paths_per_mechanism=40,
           independent_count_warning='Monte Carlo paths and origins are NOT independent experimental runs',optimization_authorized=False))
    # D4 tested command shifts are a separate out-of-distribution stress check.
    stress=[]
    for s in json.loads((D4/'pair_log.json').read_text()):
        if s['split']!='test' or not s['delta']:continue
        with np.load(Path(s['folder'])/'trajectory.npz') as raw:x=observed(raw['XMEAS'][::10],raw['XMV'][::10])
        # Last pre-action command known at5399s; input measurements at5400 are pre-integration.
        h=x[:541].copy();value=float(x[540,5]);h[-1,5]=x[539,5]
        forecast=evaluate_all_mechanisms(ensembles,h,59,58000+s['seed']+s['delta'],dict(value=value,duration_seconds=120))
        ids=np.array([0,2,5,11,29]);lo=forecast['lower'][ids,:3]-q[:5];hi=forecast['upper'][ids,:3]+q[:5]
        truth=x[541+ids,:3]
        record=dict(seed=s['seed'],fault_truth_offline=s['fault_id'],delta=s['delta'],covered=((truth>=lo)&(truth<=hi)).tolist(),
                    covered_all=bool(((truth>=lo)&(truth<=hi)).all()),optimization_allowed=False,
                    reason='PI-calibrated interval, intervention domain shift; only five test seeds, no validated intervention coverage')
        stress.append(record)
    write_json(ROOT/'d4_intervention_stress.json',stress)
    print('D5.1 completed; no optimizer was created or executed')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');args=ap.parse_args()
    freeze() if args.freeze else main()
