from pathlib import Path
import json
import numpy as np
from causalverse.causal.dynamic import DynamicModel
from causalverse.data.manifest import write_json,digest

root=Path('artifacts/d4');before=json.loads((root/'protected_before.json').read_text())
unchanged=all(digest(p)==h for p,h in before.items())
pair=json.loads((root/'pair_log.json').read_text());checks=[]
for r in pair:
    folder=Path(r['folder']);m=json.loads((folder/'manifest.json').read_text())
    assert all(digest(folder/p)==h for p,h in m['sha256'].items())
    with np.load(folder/'trajectory.npz') as d:
        finite=all(np.isfinite(d[k]).all() for k in d.files)
    checks.append(dict(folder=str(folder),finite=bool(finite),hashes=True,full_horizon=r['completed']==6000,terminated=r['terminated'],replay=r['replay_identical'],rng=r['rng_paired']))
diagnostics={}
for kind in ('SCM','VAR'):
    p=np.load(root/f'{kind}_model.npz');lag=int(p['lag']);A=np.zeros((7*lag,7*lag));A[:7]=p['coef'][1:].T
    if lag>1:A[7:,:-7]=np.eye(7*(lag-1))
    radius=float(np.max(np.abs(np.linalg.eigvals(A))))
    model=DynamicModel(lag,float(p['alpha']),kind=='SCM')
    for k in ('mean','scale','coef','noise'):setattr(model,k,p[k])
    residuals=[]
    for f in (root/'observations').glob('train_f00_*.npz'):
        with np.load(f) as d:residuals.append(model.residuals(d['values'][180:]))
    corr=np.corrcoef(np.concatenate(residuals).T);np.savez(root/f'{kind}_residual_diagnostics.npz',correlation=corr)
    off=corr-np.eye(7)
    diagnostics[kind]=dict(spectral_radius=radius,max_residual_cross_correlation=float(np.max(np.abs(off))))
write_json(root/'audit.json',dict(protected_d2_d3_unchanged=unchanged,protected_files=len(before),pairs=checks,model_diagnostics=diagnostics))
assert unchanged and len(checks)==144
assert all(c['finite'] and c['full_horizon'] and not c['terminated'] and c['replay'] for c in checks)
print('Protected artifacts unchanged; 144 paired trajectories valid; model diagnostics',diagnostics)
