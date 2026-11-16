"""Check retained artifacts, pinned vendor and fresh-environment replay."""
import hashlib
import json
from pathlib import Path
import numpy as np
import tep
from causalverse.simulation import TEPAdapter

out=Path('artifacts/d2')
review={}
vendor=Path(tep.__file__).parent
provenance=json.loads((vendor/'PROVENANCE.json').read_text())
review['installed_engine_matches_pinned_hashes']=all(hashlib.sha256((vendor/p).read_bytes()).hexdigest()==v for p,v in provenance['sha256'].items())
review['import_path']=str(vendor)
for fid in (4,11,14):
    repeat=TEPAdapter(12345); repeat.inject_fault(fid,onset_seconds=1800); repeat.run(14400)
    repeat.save(out/f'fault_{fid}_repeat_clean_env')
    prior=np.load(out/f'fault_{fid}'/'trajectory.npz')
    review[f'clean_replay_{fid}']=np.array_equal(prior['XMEAS'],np.array([r['XMEAS'] for r in repeat.rows]))
for folder in out.iterdir():
    if not folder.is_dir() or not (folder/'manifest.json').exists(): continue
    m=json.loads((folder/'manifest.json').read_text())
    d=np.load(folder/'trajectory.npz')
    review[folder.name]=dict(records=len(d['t_seconds']),finite=bool(all(np.isfinite(d[k]).all() for k in d.files)),
       measurement_columns=d['XMEAS'].shape[1],control_columns=d['XMV'].shape[1],
       hashes_match=all(hashlib.sha256((folder/p).read_bytes()).hexdigest()==v for p,v in m['sha256'].items()),
       inlet_before=float(d['coolant_inlet_temperature'][1799]) if len(d['t_seconds'])>1800 else None,
       inlet_at_onset=float(d['coolant_inlet_temperature'][1800]) if len(d['t_seconds'])>1800 else None,
       inlet_after_std=float(np.std(d['coolant_inlet_temperature'][1800:])))
(out/'artifact_review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
print(json.dumps(review,indent=2))
assert review['installed_engine_matches_pinned_hashes']
assert all(review[f'clean_replay_{f}'] for f in (4,11,14))
assert all(v['finite'] and v['hashes_match'] for v in review.values() if isinstance(v,dict))
