"""Per-run conditional Granger screening; exploratory under closed-loop errors."""
from pathlib import Path
import numpy as np
from scipy.stats import f
from causalverse.causal.dynamic import design,NAMES,PARENTS
from causalverse.data.manifest import write_json

root=Path('artifacts/d4');model=np.load(root/'VAR_model.npz');lag=int(model['lag']);edges=[(s,t) for s in range(7) for t in range(7) if s!=t];selections=[];gains=[]
for file in sorted((root/'observations').glob('train_f00_*.npz')):
    x=np.load(file)['values'][180:];z=(x-model['mean'])/model['scale'];X=design(z,lag);Y=z[lag:]
    B=np.linalg.lstsq(X,Y,rcond=None)[0];rss=np.sum((Y-X@B)**2,axis=0);ps=[];gs=[]
    for s,t in edges:
        keep=[i for i in range(X.shape[1]) if i not in [1+k*7+s for k in range(lag)]]
        A=X[:,keep];rss0=np.sum((Y[:,t]-A@np.linalg.lstsq(A,Y[:,t],rcond=None)[0])**2)
        statistic=max(0,(rss0-rss[t])/lag/(rss[t]/(len(Y)-X.shape[1])))
        ps.append(float(f.sf(statistic,lag,len(Y)-X.shape[1])));gs.append(float((rss0-rss[t])/max(rss0,1e-12)))
    order=np.argsort(ps);cut=0
    for k,i in enumerate(order,1):
        if ps[i]<=.05*k/len(ps):cut=k
    selected=np.zeros(42,bool);selected[order[:cut]]=True;selections.append(selected);gains.append(gs)
rows=[]
for i,(s,t) in enumerate(edges):
    freq=float(np.mean(np.array(selections)[:,i]));rows.append(dict(source=NAMES[s],target=NAMES[t],per_run_BH_selection_fraction=freq,
        stable_candidate=freq>=.5,median_prediction_gain=float(np.median(np.array(gains)[:,i])),process_prior=s in PARENTS[t]))
write_json(root/'granger_per_run_screen.json',rows)
