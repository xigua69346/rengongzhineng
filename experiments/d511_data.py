import argparse,json,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from causalverse.simulation import TEPAdapter
from causalverse.causal.dynamic import observed
from causalverse.data.manifest import write_json,digest

R=Path('artifacts/d5_1_1')
def one(seed,split,root):
    root=Path(root);start=time.perf_counter();parent=TEPAdapter(seed).run(3600);snap=parent.snapshot();records=[]
    for mechanism in (0,4,11,14):
        f=TEPAdapter().restore(snap)
        if mechanism:f.inject_fault(mechanism)
        f.run(1800);base=None;history=np.array([observed(r['XMEAS'][None,:],r['XMV'][None,:])[0] for r in f.rows[5340:5400:10]])
        command=float(f.get_control_variables()[9])
        for delta in (0,1,5):
            sim=f.branch();folder=root/'raw'/f'{split}_{seed}_m{mechanism}_a{delta}'
            if folder.exists():raise FileExistsError(str(folder))
            if delta:sim.set_control(10,command+delta,duration_seconds=120,action_id=f'plus_{delta}')
            sim.run(721);manifest=sim.save(folder)
            with np.load(folder/'trajectory.npz') as d:
                y=observed(d['XMEAS'][5400:],d['XMV'][5400:]);rng=d['rng_state'][5400:].copy()
                if base is None:base=(y.copy(),rng.copy())
                data=dict(history=history,command=command,values=y,rng_paired=np.array_equal(rng,base[1]),delta_values=y-base[0])
                derived=root/'observed'/folder.name;derived.parent.mkdir(exist_ok=True);np.savez_compressed(derived.with_suffix('.npz'),**data)
                stuck_target=d['valve_target'][5400,9];actualpos=d['valve_position'][5400,9]
            records.append(dict(seed=seed,split=split,mechanism=mechanism,delta=delta,folder=str(folder),
                rng_paired=bool(data['rng_paired']),termination=sim.termination_reason,records=len(sim.rows),
                command_before=command,command_requested=command+delta,accepted_target=float(stuck_target),actual_position=float(actualpos),
                snapshot_id=f'{seed}_m{mechanism}_t5400',action_end=5520,recovery_observation_end=6120))
    return records,time.perf_counter()-start

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--freeze',action='store_true');a=ap.parse_args();R.mkdir(exist_ok=True,parents=True)
    if a.pilot:
        records,elapsed=one(610999,'pilot',R/'pilot');write_json(R/'pilot_timing.json',dict(seconds=elapsed,estimated_full_seconds=elapsed*60/4,records=records));print(elapsed);return
    if a.freeze:
        if (R/'protocol.json').exists():raise FileExistsError('Already frozen')
        protected=[p for b in ['artifacts/d2','artifacts/d3','artifacts/d4','artifacts/d5'] for p in Path(b).rglob('*') if p.is_file()]
        protected.extend(p for p in Path('src/causalverse').rglob('*.py'))
        write_json(R/'protected.json',{str(p):digest(p) for p in protected})
        write_json(R/'protocol.json',dict(seeds={s:list(range(b,b+20)) for s,b in [('train',611000),('calibration',621000),('test',631000)]},
            actions=[0,1,5],duration_seconds=120,origin=5400,fault_onset=3600,recovery_seconds=600,horizons=[10,30,60,120,300,600],
            members=20,ridge=10.,coverage=.9,mae_limits=[.25,.5,5.],width_limits=[1.,2.,20.],bootstrap_seed=640001,
            calibration='max over all mechanisms,actions,horizons,targets per seed; actionwise comparator max excluding actions',
            gate='joint coverage >=.9, per target worst MAE/mean width within limits, support and stability; optimization always false'))
        return
    if (R/'data_log.json').exists():raise FileExistsError('Existing dataset')
    plan=json.loads((R/'protocol.json').read_text());rows=[];start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(one,seed,s,str(R)) for s,seeds in plan['seeds'].items() for seed in seeds]):
            r,seconds=f.result();rows+=r;write_json(R/'data_log.json',dict(elapsed=time.perf_counter()-start,runs=rows));print(len(rows),flush=True)
if __name__=='__main__':main()
