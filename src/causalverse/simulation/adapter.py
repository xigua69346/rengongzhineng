"""One-second Python TEP adapter. External IDs are strictly one-based."""
import copy
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np
from tep import TEPSimulator

ENGINE_COMMIT = '9a6c8e5fcef4a2850778704e7793c87b0a187005'


def integer(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError('Expected integer >= %d' % minimum)
    return int(value)


class SelectiveController:
    """Run every original PI loop; replace only scheduled output channels.

    The original incremental PI sees the applied command on the next tick.
    This is explicit output tracking, not a promise of bumpless release.
    """
    def __init__(self, original):
        self.original = original
        self.actions = []
        self.pi_command = None
        self.applied_command = None

    def calculate(self, xmeas, xmv, time_step):
        proposal = self.original.calculate(xmeas, xmv, time_step)
        applied = proposal.copy()
        for action in self.actions:
            if action['start'] <= time_step < action['end']:
                applied[action['index']-1] = action['value']
        self.pi_command = proposal.copy()
        self.applied_command = applied.copy()
        return applied


@dataclass(frozen=True)
class Snapshot:
    engine_commit: str
    payload: object


class TEPAdapter:
    def __init__(self, random_seed=4651207995):
        self.random_seed = integer(random_seed)
        self.initialize()

    def initialize(self):
        self.sim = TEPSimulator(random_seed=self.random_seed, backend='python')
        self.sim.initialize()
        self.sim.controller = SelectiveController(self.sim.controller)
        self.faults = []
        self.rows = []
        self.run_id = uuid4().hex
        self.parent_run_id = None
        self.termination_reason = None
        return self

    def reset(self, random_seed=None):
        if random_seed is not None:
            self.random_seed = integer(random_seed)
        return self.initialize()

    @property
    def t_seconds(self):
        return self.sim.step_count

    def get_measurements(self):
        return self.sim.get_measurements().copy()

    def get_control_variables(self):
        return self.sim.get_manipulated_vars().copy()

    def set_control(self, index, value, *, duration_seconds, start_seconds=None, action_id=None):
        index = integer(index, 1)
        start = self.t_seconds if start_seconds is None else integer(start_seconds)
        duration = integer(duration_seconds, 1)
        if index > 12 or start < self.t_seconds or not np.isfinite(value) or not 0 <= value <= 100:
            raise ValueError('Invalid control ID, time or percentage')
        end = start + duration
        for a in self.sim.controller.actions:
            if a['index'] == index and max(start, a['start']) < min(end, a['end']):
                raise ValueError('Overlapping actions on one output')
        action = dict(index=index, value=float(value), start=start, end=end,
                      action_id=action_id or uuid4().hex, mode='absolute_output_override',
                      command_before_scheduling=float(self.get_control_variables()[index-1]))
        self.sim.controller.actions.append(action)
        return copy.deepcopy(action)

    def inject_fault(self, fault_id, *, onset_seconds=None):
        fault_id = integer(fault_id, 1)
        onset = self.t_seconds if onset_seconds is None else integer(onset_seconds)
        if fault_id > 20 or onset < self.t_seconds:
            raise ValueError('Invalid fault ID or onset')
        if any(f['fault_id'] == fault_id for f in self.faults):
            raise ValueError('Fault already scheduled')
        self.faults.append(dict(fault_id=fault_id, fault_onset=onset))

    def step(self):
        if self.termination_reason:
            raise RuntimeError('Run terminated: '+self.termination_reason)
        t = self.t_seconds
        for fault in self.faults:
            if t == fault['fault_onset']:
                self.sim.set_disturbance(fault['fault_id'], 1)
        before = self.get_control_variables()
        running = self.sim.step()
        p = self.sim.process
        row = dict(t_seconds=t, state_t_seconds=self.t_seconds,
                   XMEAS=self.get_measurements(), XMV=self.get_control_variables(),
                   command_before=before, pi_command=self.sim.controller.pi_command.copy(),
                   valve_position=p.yy[38:50].copy(), valve_target=p._teproc.vcv.copy(),
                   idv=p._idv.copy(), rng_state=float(p._g),
                   coolant_inlet_temperature=float(p._teproc.tcwr))
        finite = all(np.isfinite(row[k]).all() for k in ('XMEAS','XMV','valve_position')) and np.isfinite(p.yy).all()
        if not finite:
            self.termination_reason = 'non_finite'
        elif not running:
            self.termination_reason = 'plant_shutdown' if self.sim.is_shutdown() else 'integration_failure'
        self.rows.append(row)
        return copy.deepcopy(row)

    def run(self, duration_seconds):
        for _ in range(integer(duration_seconds)):
            if self.termination_reason:
                break
            self.step()
        return self

    def snapshot(self):
        # One deepcopy preserves aliasing, including wrappers pointing to process.
        return Snapshot(ENGINE_COMMIT, copy.deepcopy(self.__dict__))

    def restore(self, snapshot):
        if not isinstance(snapshot, Snapshot) or snapshot.engine_commit != ENGINE_COMMIT:
            raise ValueError('Incompatible snapshot')
        self.__dict__ = copy.deepcopy(snapshot.payload)
        return self

    def branch(self):
        child = object.__new__(TEPAdapter)
        child.restore(self.snapshot())
        child.parent_run_id = self.run_id
        child.run_id = uuid4().hex
        return child

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        keys = list(self.rows[0]) if self.rows else ['t_seconds','XMEAS','XMV']
        arrays = {k: np.array([r[k] for r in self.rows]) for k in keys}
        np.savez_compressed(directory/'trajectory.npz', **arrays)
        header = ['t_seconds','state_t_seconds']+[f'XMEAS({i})' for i in range(1,42)]+[f'XMV({i})' for i in range(1,13)]+[f'valve_position({i})' for i in range(1,13)]
        with (directory/'trajectory.csv').open('w',newline='',encoding='utf-8') as fp:
            writer = csv.writer(fp); writer.writerow(header)
            for r in self.rows:
                writer.writerow([r['t_seconds'],r['state_t_seconds'],*r['XMEAS'],*r['XMV'],*r['valve_position']])
        # Observation at beginning of each 1s step; exact decimation, no averaging.
        mask = arrays['t_seconds'] % 180 == 0
        np.savez_compressed(directory/'aligned_180s.npz', **{k:v[mask] for k,v in arrays.items()})
        manifest = dict(schema_version=1, run_id=self.run_id, parent_run_id=self.parent_run_id,
                        engine_commit=ENGINE_COMMIT, backend='python',random_seed=self.random_seed,
                        fault_id=[f['fault_id'] for f in self.faults], fault_onset=[f['fault_onset'] for f in self.faults],
                        fault_schedule=self.faults, controller_mode='closed_loop_selective_output_override',
                        action_id=[a['action_id'] for a in self.sim.controller.actions], action_schedule=self.sim.controller.actions,
                        termination_reason=self.termination_reason or 'requested_horizon_completed',
                        completed_seconds=self.t_seconds, records=len(self.rows), sample_interval_seconds=1,
                        measurement_time='t_seconds: pre-integration evaluation; valve_position at state_t_seconds',
                        alignment='t_seconds modulo 180 equals zero; no interpolation',
                        sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.suffix in ('.csv','.npz')})
        (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        return manifest
