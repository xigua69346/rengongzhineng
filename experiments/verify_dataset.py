"""Audit all runs and replay four preregistered representative runs."""
import json
from pathlib import Path
import numpy as np
from causalverse.simulation import TEPAdapter
from causalverse.data.manifest import digest,write_json
from causalverse.data.preprocessing import validate,process

root=Path('artifacts/d3/dataset');plan=json.loads((root/'split_plan.json').read_text());report=[]
for spec in plan['runs']:
    folder=root/'raw'/spec['dataset_run_id'];m=json.loads((folder/'manifest.json').read_text())
    assert m['dataset_plan_sha256']==digest(root/'split_plan.json')
    assert m['seed']==spec['seed'] and m['split']==spec['split']
    assert all(digest(folder/p)==v for p,v in m['sha256'].items())
    with np.load(folder/'trajectory.npz') as d:
        validate(d['t_seconds'],d['XMEAS'],d['XMV'],plan['horizon_seconds'])
        processed=process(d['t_seconds'],d['XMEAS'],d['XMV'],spec['fault_id'],plan['onset_seconds'])
        with np.load(root/'processed'/f"{spec['dataset_run_id']}.npz") as p:
            assert all(np.array_equal(v,p[k]) for k,v in processed.items())
        if spec['fault_id']:
            assert np.array_equal(d['idv'][:,spec['fault_id']-1],(d['t_seconds']>=plan['onset_seconds']).astype(int))
    report.append(dict(run_id=spec['dataset_run_id'],hashes_match=True,complete=True,processed_matches=True))
write_json(root/'integrity_audit.json',report)
replay=[]
for fault in (0,4,11,14):
    s=next(s for s in plan['runs'] if s['split']=='test' and s['fault_id']==fault)
    sim=TEPAdapter(s['seed'])
    if fault:sim.inject_fault(fault,onset_seconds=plan['onset_seconds'])
    sim.run(plan['horizon_seconds']);sim.save(Path('artifacts/d3/replay')/s['dataset_run_id'])
    with np.load(root/'raw'/s['dataset_run_id']/'trajectory.npz') as d:
        equal=all(np.array_equal(d[k],np.array([r[k] for r in sim.rows])) for k in d.files)
    replay.append(dict(run_id=s['dataset_run_id'],all_raw_arrays_identical=equal,tolerance=0))
write_json(root/'reproduction_audit.json',replay)
assert all(r['all_raw_arrays_identical'] for r in replay)
print('All 200 run manifests/hashes/processed arrays and 4 full replays passed')
