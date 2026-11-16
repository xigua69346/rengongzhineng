import json
from pathlib import Path
from causalverse.simulation import TEPAdapter
from .preprocessing import validate, process
from .manifest import write_json, digest
import numpy as np

def generate_one(root, plan, spec):
    root=Path(root); folder=root/'raw'/spec['dataset_run_id']
    if folder.exists(): raise FileExistsError(str(folder))
    sim=TEPAdapter(spec['seed'])
    if spec['fault_id']: sim.inject_fault(spec['fault_id'],onset_seconds=plan['onset_seconds'])
    sim.run(plan['horizon_seconds']); m=sim.save(folder)
    m.update(spec)
    m.update(dataset_plan_sha256=digest(root/'split_plan.json'),requested_horizon_seconds=plan['horizon_seconds'],
             fault_duration_seconds=plan['fault_duration_seconds'] if spec['fault_id'] else 0,
             actual_fault_duration_seconds=max(0,sim.t_seconds-plan['onset_seconds']) if spec['fault_id'] else 0)
    write_json(folder/'manifest.json',m)
    try:
        d={k:np.array([r[k] for r in sim.rows]) for k in ('t_seconds','XMEAS','XMV')}
        validate(**dict(t=d['t_seconds'],measurements=d['XMEAS'],controls=d['XMV']),expected_length=plan['horizon_seconds'])
        p=process(d['t_seconds'],d['XMEAS'],d['XMV'],spec['fault_id'],plan['onset_seconds'],plan['warmup_seconds'],plan['sample_seconds'])
        (root/'processed').mkdir(exist_ok=True)
        np.savez_compressed(root/'processed'/f"{spec['dataset_run_id']}.npz",**p)
        status='complete'
    except Exception as e:
        status=f'failed: {e}'
    return dict(**spec,status=status,termination_reason=m['termination_reason'],records=len(sim.rows))
