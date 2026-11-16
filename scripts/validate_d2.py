"""Actual integration runs and retained failures. Run from installed package."""
import json
from pathlib import Path
import numpy as np
from causalverse.simulation import TEPAdapter

OUT=Path('artifacts/d2')
OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'results.json').exists():
    raise RuntimeError('Archive existing artifacts/d2 before a new validation run')
checks=[]
def check(name, condition, **detail):
    checks.append(dict(name=name,passed=bool(condition),**detail))
    (OUT/'results.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(name, bool(condition),detail,flush=True)

normal=TEPAdapter(12345).run(86400)
normal.save(OUT/'normal_24h')
check('normal_24h',normal.t_seconds==86400 and normal.termination_reason is None)
del normal
for fid in (4,11,14):
    sim=TEPAdapter(12345); sim.inject_fault(fid,onset_seconds=1800); sim.run(14400)
    sim.save(OUT/f'fault_{fid}')
    check(f'fault_{fid}_onset',all(r['idv'][fid-1]==int(r['t_seconds']>=1800) for r in sim.rows),first_active=next(r['t_seconds'] for r in sim.rows if r['idv'][fid-1]))
    check(f'fault_{fid}_finite_horizon',sim.t_seconds==14400 and sim.termination_reason is None)
    repeat=TEPAdapter(12345); repeat.inject_fault(fid,onset_seconds=1800); repeat.run(14400)
    repeat.save(OUT/f'fault_{fid}_repeat')
    check(f'fault_{fid}_same_seed',all(np.array_equal(x['XMEAS'],y['XMEAS']) for x,y in zip(sim.rows,repeat.rows)) and len(sim.rows)==len(repeat.rows))
    other=TEPAdapter(54321); other.inject_fault(fid,onset_seconds=1800); other.run(14400); other.save(OUT/f'fault_{fid}_seed54321')
    check(f'fault_{fid}_different_seed',not np.array_equal(sim.rows[-1]['XMEAS'],other.rows[-1]['XMEAS']))
    del sim,repeat,other

history=TEPAdapter(12345); history.inject_fault(14,onset_seconds=1800); history.run(3600)
snap=history.snapshot(); base=history.branch(); twin=history.branch()
base.run(600); twin.run(600)
check('same_history_branches',all(np.array_equal(x['XMEAS'],y['XMEAS']) and x['rng_state']==y['rng_state'] for x,y in zip(base.rows,twin.rows)))
restored=TEPAdapter().restore(snap).run(600)
check('snapshot_restore',all(np.array_equal(x['XMEAS'],y['XMEAS']) for x,y in zip(base.rows,restored.rows)))
base.save(OUT/'baseline_branch')
target=float(history.sim.process._teproc.vcv[9])
for delta in (1.0,5.0):
    arm=history.branch(); arm.set_control(10,target+delta,duration_seconds=120,action_id=f'coolant_plus_{delta}')
    arm.run(600); arm.save(OUT/f'action_{delta}')
    active=arm.rows[3600:3720]; first=active[0]
    check(f'command_{delta}',all(r['XMV'][9]==target+delta for r in active))
    check(f'selective_{delta}',all(np.array_equal(np.delete(r['XMV'],9),np.delete(r['pi_command'],9)) for r in active))
    observed_target=float(first['valve_target'][9])
    check(f'stiction_{delta}',abs(observed_target-(target if delta==1 else target+delta))<1e-12, prior_target=target,command=target+delta,accepted_target=observed_target,first_actual_position=float(first['valve_position'][9]))
    check(f'paired_rng_{delta}',all(x['rng_state']==y['rng_state'] for x,y in zip(base.rows,arm.rows)))
    check(f'action_{delta}_horizon',arm.t_seconds==4200 and arm.termination_reason is None)
check('all_integration_checks',all(c['passed'] for c in checks))
if not all(c['passed'] for c in checks):
    raise SystemExit('Integration checks failed; retained results.json and trajectories')
