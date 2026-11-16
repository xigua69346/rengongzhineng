"""Fit train, calibrate validation, freeze model, then evaluate test once."""
import csv,json
from pathlib import Path
import numpy as np
from causalverse.data.dataset import load_runs
from causalverse.data.preprocessing import Standardizer,MEASUREMENTS
from causalverse.data.manifest import write_json,digest
from causalverse.detection.threshold import ThresholdDetector
from causalverse.detection.pca import PCADetector
from causalverse.detection.statistics import control_limit
from causalverse.detection.evaluation import metrics,delay

ROOT=Path('artifacts/d3/dataset');OUT=Path('artifacts/d3/detection')

def main():
    if OUT.exists(): raise FileExistsError('Archive detection outputs before rerunning')
    OUT.mkdir(parents=True)
    plan=json.loads((ROOT/'split_plan.json').read_text())
    log=json.loads((ROOT/'generation_log.json').read_text())
    assert len(log['runs'])==len(plan['runs']) and all(r['status']=='complete' for r in log['runs'])
    train=load_runs(ROOT,'train'); val=load_runs(ROOT,'validation')
    normal=[d['XMEAS'] for s,d in train if s['fault_id']==0]
    scaler=Standardizer().fit(np.concatenate(normal));z=scaler.transform(np.concatenate(normal))
    threshold=ThresholdDetector().fit(z); pca=PCADetector().fit(z,plan['protocol']['pca_variance'])
    vz=scaler.transform(np.concatenate([d['XMEAS'] for s,d in val if s['fault_id']==0]));vs=pca.scores(vz)
    limits=dict(Threshold=control_limit(threshold.score(vz),0.99),T2=control_limit(vs['T2'],0.995),SPE=control_limit(vs['SPE'],0.995))
    np.savez(OUT/'model.npz',mean=scaler.mean,scale=scaler.scale,constant=scaler.constant,
             threshold_center=threshold.center,threshold_width=threshold.width,pca_center=pca.center,
             components=pca.components,eigenvalues=pca.eigenvalues,explained_variance=pca.explained_variance,explained_ratio=pca.ratio)
    write_json(OUT/'model_manifest.json',dict(plan_sha256=digest(ROOT/'split_plan.json'),limits=limits,
               fit_runs=[s['dataset_run_id'] for s,d in train if s['fault_id']==0],
               calibration_runs=[s['dataset_run_id'] for s,d in val if s['fault_id']==0],
               measurement_ids=list(range(1,42)),controls_used=False,internals_used=False,
               retained_components=len(pca.components),model_sha256=digest(OUT/'model.npz'),
               explained_ratio=pca.ratio.tolist(),cumulative_explained_ratio=np.cumsum(pca.ratio).tolist(),
               calibration='empirical normal validation quantiles, higher; Threshold .99, T2/SPE .995, PCA OR'))
    # Test data first opened only after model and control limits are persisted.
    tests=load_runs(ROOT,'test'); all_runs=[]; inference={}; contributions={f:[] for f in (4,11,14)}
    for spec,d in tests:
        z=scaler.transform(d['XMEAS']);ps=pca.scores(z); scores=dict(Threshold=threshold.score(z),T2=ps['T2'],SPE=ps['SPE'])
        pred={k:v>limits[k] for k,v in scores.items()};pred['PCA']=pred['T2']|pred['SPE']
        rid=spec['dataset_run_id']; inference[rid]=(spec,d,pred,scores)
        np.savez_compressed(OUT/f'{rid}.npz',t_seconds=d['t_seconds'],y=d['y'],projection=ps['projection'],
                            T2=ps['T2'],SPE=ps['SPE'],threshold_score=scores['Threshold'],
                            T2_contribution=ps['T2_contribution'],SPE_contribution=ps['SPE_contribution'],
                            threshold_contribution=threshold.contributions(z),**{f'pred_{k}':v for k,v in pred.items()})
        for name,p in pred.items():
            m=metrics(d['y'],p);m.update(run_id=rid,seed=spec['seed'],fault_id=spec['fault_id'],detector=name,
                detection_delay_seconds=delay(d['t_seconds'],p,plan['onset_seconds']) if spec['fault_id'] else None,
                pre_onset_false_alarms=int(p[d['t_seconds']<plan['onset_seconds']].sum()))
            all_runs.append(m)
        if spec['fault_id']:
            contributions[spec['fault_id']].append(np.mean((ps['T2_contribution']/limits['T2']+ps['SPE_contribution']/limits['SPE'])[d['y']==1],axis=0))
    aggregate=[]
    for fid in (0,4,11,14):
        selected=[(s,d,p) for s,d,p,sc in inference.values() if s['fault_id'] in ({0,fid} if fid else {0})]
        for name in ('Threshold','T2','SPE','PCA'):
            m=metrics(np.concatenate([d['y'] for s,d,p in selected]),np.concatenate([p[name] for s,d,p in selected]))
            rows=[r for r in all_runs if r['fault_id']==fid and r['detector']==name];delays=[r['detection_delay_seconds'] for r in rows if r['detection_delay_seconds'] is not None]
            m.update(fault_id=fid,detector=name,runs=len(selected),detected_fault_runs=len(delays) if fid else None,
                     delay_mean_seconds=float(np.mean(delays)) if delays else None,
                     delay_min_seconds=min(delays) if delays else None,delay_max_seconds=max(delays) if delays else None,
                     recall_min=min(r['Recall'] for r in rows),recall_max=max(r['Recall'] for r in rows),
                     recall_std=float(np.std([r['Recall'] for r in rows])))
            aggregate.append(m)
    write_json(OUT/'metrics.json',aggregate);write_json(OUT/'per_run_metrics.json',all_runs)
    top={str(fid):[dict(variable=MEASUREMENTS[i],mean_score=float(v[i])) for i in np.argsort(-v)[:10]] for fid,vals in contributions.items() for v in [np.mean(vals,axis=0)]}
    write_json(OUT/'contributions.json',top)
    for name,rows in [('metrics',aggregate),('per_run_metrics',all_runs)]:
        with (OUT/f'{name}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Retain every false-positive/false-negative time point, not only examples.
    with (OUT/'error_cases.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['run_id','fault_id','detector','t_seconds','truth','prediction','error'])
        for rid,(s,d,p,sc) in inference.items():
            for name,pred in p.items():
                for i in np.flatnonzero(pred!=d['y']): w.writerow([rid,s['fault_id'],name,int(d['t_seconds'][i]),int(d['y'][i]),int(pred[i]),'FP' if pred[i] else 'FN'])
    visualize(inference,limits,plan)
    print(json.dumps(aggregate,indent=2))

def visualize(inference,limits,plan):
    from plotly.offline import get_plotlyjs
    payload={rid:dict(fault=s['fault_id'],seed=s['seed'],t=d['t_seconds'].tolist(),
       temperature=d['XMEAS'][:,8].tolist(),coolant_outlet=d['XMEAS'][:,20].tolist(),
       pressure=d['XMEAS'][:,6].tolist(),truth=d['y'].tolist(),
       predictions={k:v.astype(int).tolist() for k,v in pred.items()},scores={k:v.tolist() for k,v in scores.items()})
       for rid,(s,d,pred,scores) in inference.items()}
    html='''<!doctype html><html lang="zh"><meta charset="utf-8"><title>CausalVerse D3 检测实验</title>
<style>body{font:16px system-ui;margin:30px;background:#f4f6f8;color:#182735}select{padding:8px;margin:8px}.chart{height:330px;background:white;margin:16px 0}</style>
<h1>CausalVerse D3 实验分析</h1><p>全部80条独立测试运行。贡献度不是因果根因。180秒采样；故障时刻3600秒；不显示最佳种子筛选。</p>
<label>运行<select id="run"></select></label><label>检测器<select id="detector"><option>PCA</option><option>Threshold</option><option>T2</option><option>SPE</option></select></label>
<div id="summary"></div><div id="variables" class="chart"></div><div id="statistics" class="chart"></div><div id="labels" class="chart"></div><script>'''+get_plotlyjs()+'''</script><script>
const runs=PAYLOAD, limits=LIMITS;
const select=document.getElementById('run'),det=document.getElementById('detector');Object.keys(runs).forEach(k=>{let o=document.createElement('option');o.textContent=k;select.append(o)});
function draw(){let r=runs[select.value],name=det.value;document.getElementById('summary').textContent='seed='+r.seed+' / IDV='+r.fault;
let shape=r.fault?[{type:'line',xref:'x',yref:'paper',x0:3600,x1:3600,y0:0,y1:1,line:{color:'red',dash:'dash'}}]:[];
let layout={margin:{t:45},shapes:shape,xaxis:{title:{text:'仿真时间 / s'}}};
Plotly.newPlot('variables',[{x:r.t,y:r.temperature,name:'XMEAS(9) 反应釜温度 °C'},{x:r.t,y:r.coolant_outlet,name:'XMEAS(21) 冷却水出口 °C'},{x:r.t,y:r.pressure,name:'XMEAS(7) 压力 kPa',yaxis:'y2'}],{...layout,title:{text:'过程测量'},yaxis2:{overlaying:'y',side:'right'}},{responsive:true});
Plotly.newPlot('statistics',['T2','SPE','Threshold'].map(k=>({x:r.t,y:r.scores[k].map(v=>v/limits[k]),name:k+' / 控制限'})),{...layout,title:{text:'T²、SPE 与阈值统计量（1为控制限）'},yaxis:{type:'log'}},{responsive:true});
Plotly.newPlot('labels',[{x:r.t,y:r.truth,name:'真实故障标签',line:{shape:'hv'}},{x:r.t,y:r.predictions[name],name:name+' 异常判定',line:{shape:'hv',dash:'dot'}}],{...layout,title:{text:'故障时间段与检测判定'}},{responsive:true});}
select.onchange=draw;det.onchange=draw;draw();</script></html>'''
    html=html.replace('PAYLOAD',json.dumps(payload)).replace('LIMITS',json.dumps(limits))
    (OUT/'experiment.html').write_text(html,encoding='utf-8')

if __name__=='__main__':main()
