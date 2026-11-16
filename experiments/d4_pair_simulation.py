import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from causalverse.simulation import TEPAdapter
from causalverse.data.manifest import write_json

ROOT=Path('artifacts/d4')
def one(spec):
    parent=TEPAdapter(spec['seed']).run(3600); snapshot=parent.snapshot();records=[]
    for fid in (0,4,11,14):
        fault=TEPAdapter().restore(snapshot)
        if fid:fault.inject_fault(fid)
        fault.run(1800)
        twin=fault.branch(); check=fault.branch();twin.run(20);check.run(20)
        replay=all(np.array_equal(a['XMEAS'],b['XMEAS']) for a,b in zip(twin.rows,check.rows))
        branches={}
        for delta in (0,1,5):
            sim=fault.branch()
            if delta:sim.set_control(10,float(fault.get_control_variables()[9]+delta),duration_seconds=120,action_id=f'probe_plus_{delta}')
            sim.run(600); folder=ROOT/'pairs'/f"{spec['split']}_{spec['seed']}_f{fid}_a{delta}"
            sim.save(folder);branches[delta]=sim
        base=branches[0]
        for delta,sim in branches.items():
            records.append(dict(**spec,fault_id=fid,delta=delta,folder=str(ROOT/'pairs'/f"{spec['split']}_{spec['seed']}_f{fid}_a{delta}"),
              replay_identical=replay,rng_paired=all(a['rng_state']==b['rng_state'] for a,b in zip(sim.rows,base.rows)),
              terminated=sim.termination_reason,completed=sim.t_seconds))
    # Cross-fault pairing can differ: do not assume it from shared seed.
    return records

if __name__=='__main__':
    plan=json.loads((ROOT/'protocol.json').read_text()); records=[]
    if (ROOT/'pair_log.json').exists():raise FileExistsError('Existing pair log')
    with ProcessPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(one,s) for s in plan['pair_seeds']]):
            records.extend(f.result());write_json(ROOT/'pair_log.json',records);print('paired runs',len(records),flush=True)
