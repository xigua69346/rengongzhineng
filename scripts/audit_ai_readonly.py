"""Recompute frozen-model outputs without fitting, simulation, or archive writes.

Run at repository root with PYTHONPATH=src. Only writes the new audit evidence.
"""
import json
import hashlib
import platform
from pathlib import Path
from collections import Counter
import numpy as np
import scipy
from scipy.special import softmax
from causalverse.detection.pca import PCADetector
from causalverse.detection.threshold import ThresholdDetector
from causalverse.decision.mechanism import LogisticMechanism, SmallVAR, conservative_candidates, summarize
from causalverse.causal.dynamic import MechanismEvidence, DynamicModel, static_features, residual_features
from causalverse.decision.intervention_model import ConditionalPredictor, Ridge
from causalverse.decision.intervention_calibration import calibrate
from causalverse.decision.uncertainty import MechanismEnsemble, evaluate_all_mechanisms
from causalverse.dashboard.server import api


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    sources = [p for base in ('src', 'experiments', 'tests', 'frontend/src', 'docs/research')
               for p in Path(base).rglob('*') if p.suffix in ('.py', '.svelte', '.js', '.css', '.md', '.json')]
    before = {str(p): sha(p) for p in sources}
    out = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
               purpose='Frozen-model replay verification; no training or new simulations', source_hashes=before)
    plan = read('artifacts/d3/dataset/split_plan.json')
    out['d3_split_counts'] = dict(Counter(r['split'] for r in plan['runs']))
    groups = [{r['seed'] for r in plan['runs'] if r['split'] == s} for s in ('train', 'validation', 'test')]
    assert all(not a & b for i, a in enumerate(groups) for b in groups[i+1:])
    p = np.load('artifacts/d3/detection/model.npz')
    manifest = read('artifacts/d3/detection/model_manifest.json')
    assert sha('artifacts/d3/detection/model.npz') == manifest['model_sha256']
    detector = PCADetector()
    for k in ('center', 'components', 'eigenvalues'):
        setattr(detector, k, p['pca_center' if k == 'center' else k])
    threshold = ThresholdDetector(); threshold.center=p['threshold_center']; threshold.width=p['threshold_width']
    for r in (r for r in plan['runs'] if r['split'] == 'test'):
        name=r['dataset_run_id']
        with np.load(f'artifacts/d3/dataset/processed/{name}.npz') as d, np.load(f'artifacts/d3/detection/{name}.npz') as saved:
            z=(d['XMEAS']-p['mean'])/p['scale']; result=detector.scores(z)
            for k in ('T2', 'SPE', 'T2_contribution', 'SPE_contribution'):
                np.testing.assert_allclose(result[k], saved[k], rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(threshold.score(z), saved['threshold_score'], rtol=1e-12)
            for k, v in [('T2', result['T2']), ('SPE', result['SPE']), ('Threshold', threshold.score(z))]:
                np.testing.assert_array_equal(v > manifest['limits'][k], saved[f'pred_{k}'])
            np.testing.assert_array_equal((result['T2']>manifest['limits']['T2']) | (result['SPE']>manifest['limits']['SPE']),saved['pred_PCA'])
    out['d3_reloaded_inference'] = dict(runs=80, retained_components=int(len(p['components'])), matched=True)
    records=read('artifacts/d5_1_2/diagnoses.json'); metrics=read('artifacts/d5_1_2/metrics.json')
    for kind in ('static', 'VAR', 'logistic'):
        for window in (180, 600, 1800):
            params=np.load(f'artifacts/d5_1_2/{kind}_{window}.npz')
            m=LogisticMechanism() if kind=='logistic' else MechanismEvidence()
            for k in (('mean','scale','coef') if kind=='logistic' else ('center','scale','means','variances','limits')):
                setattr(m,k,params[k])
            for split in ('test','external'):
                rs=[r for r in records if r['kind']==kind and r['window']==window and r['split']==split]
                f=np.load(f'artifacts/d5_1_2/features_{kind}_{window}.npz')
                x=f[f'{split}_x']; y=f[f'{split}_y']
                scores=m.scores(x) if kind=='logistic' else softmax(-m.distances(x),axis=1)
                sets=(1-scores<=params['thresholds']) if kind=='logistic' else (m.distances(x)<=m.limits)
                rank,sets=conservative_candidates(scores,sets)
                np.testing.assert_allclose(scores,[r['scores'] for r in rs],rtol=1e-12,atol=1e-12)
                np.testing.assert_array_equal(np.array([0,4,11,14])[rank],[r['ranking'] for r in rs])
                actual=summarize(y,rank,sets); saved=next(v for v in metrics if v['kind']==kind and v['window']==window and v['split']==split)
                for k in ('top1','macro_f1','top2','refusal','candidate_coverage','wrong_certain_all'):
                    np.testing.assert_allclose(actual[k],saved[k],rtol=1e-12)
    # Recompute features from permitted observations for each D3 test run, not just saved feature arrays.
    v=np.load('artifacts/d5_1_2/VAR_model.npz'); var=SmallVAR()
    for k in ('mean','scale','coef','noise','lag','alpha'):setattr(var,k,v[k])
    for window in (180,600,1800):
        test=[r for r in plan['runs'] if r['split']=='test']
        xs=[np.load(f"artifacts/d4/observations/{r['dataset_run_id']}.npz")['values'][:,[0,1,2,5]].copy()[360:360+window//10] for r in test]
        from causalverse.decision.mechanism import simple_features
        for kind, fn in [('static',static_features),('VAR',lambda x:residual_features(var,x)),('logistic',simple_features)]:
            saved=np.load(f'artifacts/d5_1_2/features_{kind}_{window}.npz')['test_x']
            np.testing.assert_allclose([fn(x) for x in xs],saved,rtol=1e-12,atol=1e-12)
    out['d512_reloaded_inference']=dict(decisions=len(records), d3_test_feature_windows=720, metric_rows=len(metrics), matched=True,
        metrics=metrics, external_feature_reconstruction=False)
    d511=read('artifacts/d5_1_1/protocol.json'); log=read('artifacts/d5_1_1/data_log.json')['runs']
    out['d511_counts']=dict(branches=len(log),independent_seeds={k:len(v) for k,v in d511['seeds'].items()})
    seedsets=[set(v) for v in d511['seeds'].values()]
    assert all(not a&b for i,a in enumerate(seedsets) for b in seedsets[i+1:])
    test=sorted([r for r in log if r['split']=='test'],key=lambda r:(r['seed'],r['mechanism'],r['delta']))
    errors={}
    for kind in ('action','delta'):
        p=np.load(f'artifacts/d5_1_1/{kind}_ensemble.npz'); members=[]
        for i in range(20):
            m=ConditionalPredictor(kind)
            for name in (('model',) if kind=='action' else ('model','base')):
                model=Ridge()
                for field in ('mean','scale','coef'):setattr(model,field,p[f'{i}_{name}_{field}'])
                setattr(m,name,model)
            members.append(m)
        prediction=[]
        for r in test:
            h=np.load('artifacts/d5_1_1/observed/'+Path(r['folder']).name+'.npz')['history']
            prediction.append(np.mean([m.predict(h,r['delta'],r['command_before']) for m in members],axis=0))
        saved=np.load(f'artifacts/d5_1_1/predictions_{kind}_test.npz')['predicted']
        errors[kind]=float(np.max(np.abs(prediction-saved)))
        np.testing.assert_allclose(prediction,saved,rtol=1e-12,atol=1e-12)
    for kind in ('action','delta','PI','PI_stable'):
        cal=np.load(f'artifacts/d5_1_1/predictions_{kind}_calibration.npz')
        q,qa=calibrate((cal['truth']-cal['predicted']).reshape(20,4,3,6,3),np.array([.25,.5,5.]))
        frozen=read(f'artifacts/d5_1_1/calibration_{kind}.json')
        np.testing.assert_allclose(q,frozen['joint']);np.testing.assert_allclose(qa,frozen['actionwise'])
        saved=np.load(f'artifacts/d5_1_1/intervals_{kind}_test.npz');scales=np.array([.25,.5,5.])
        np.testing.assert_allclose(saved['joint_lower'],saved['prediction']-q*scales)
        np.testing.assert_allclose(saved['joint_upper'],saved['prediction']+q*scales)
    out['d511_reloaded_inference']=dict(branches_per_model=240,members=20,max_absolute_errors=errors,calibration_models=4,matched=True)
    out['d511_summary']=read('artifacts/d5_1_1/final_summary.json')['models']
    # Reconstruct the original PI ensemble and one frozen D5.1 test forecast.
    ensembles=[]
    for c in (0,4,11,14):
        p=np.load(f'artifacts/d5/uncertainty/ensemble_m{c}.npz');e=MechanismEnsemble();e.models=[];e.banks=list(p['residual_banks'])
        for coef,mean,scale in zip(p['coef'],p['mean'],p['scale']):
            m=DynamicModel(6,.1,True);m.coef=coef;m.mean=mean;m.scale=scale;e.models.append(m)
        ensembles.append(e)
    r=next(r for r in plan['runs'] if r['split']=='test');x=np.load(f"artifacts/d4/observations/{r['dataset_run_id']}.npz")['values']
    forecast=evaluate_all_mechanisms(ensembles,x[:361],60,52001)
    saved=np.load(f"artifacts/d5/uncertainty/test/{r['dataset_run_id']}.npz");idx=np.array([1,3,6,12,30,60])-1
    for a,b in [('mean','mean'),('lower','lower'),('upper','upper')]:
        np.testing.assert_allclose(forecast[a][idx,:3],saved[b][0],rtol=1e-12,atol=1e-12)
    out['d5_forecast_replay']=dict(run=r['dataset_run_id'],origin=3600,mechanisms=4,members_per_mechanism=20,matched=True)
    out['api_checks']={}
    for path,q in [('/api/runs',{}),('/api/research',{}),('/api/trajectory',{'run':['test_f14_00']}),('/api/detection',{'run':['test_f14_00']}),('/api/diagnosis',{'run':['test_f14_00']}),('/api/uncertainty',{})]:
        data=api(path,q);json.dumps(data,allow_nan=False);out['api_checks'][path]='valid JSON from artifact adapter (not HTTP/browser test)'
    out['protected_d512']={'count':len(read('artifacts/d5_1_2/protected.json')),
        'changed':[p for p,h in read('artifacts/d5_1_2/protected.json').items() if not Path(p).exists() or sha(p)!=h]}
    assert not out['protected_d512']['changed']
    assert all(sha(p)==h for p,h in before.items())
    out['existing_sources_unchanged']=True
    target=Path('artifacts/ai_audit/verification.json');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('source_hashes','d512_reloaded_inference','d511_summary')},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
