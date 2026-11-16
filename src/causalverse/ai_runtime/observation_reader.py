"""Server-side observation projection, strict clocks and identity admission only."""
from dataclasses import replace
import uuid
import numpy as np
from .contracts import ObservationContext, InferenceRequest, require, validate_observations, validate_request
from .identity import IdentityStore, same_identity
from .provenance import stable_hash, context_payload


def seven(measurements, controls):
    return np.column_stack([measurements[:, 8], measurements[:, 20], measurements[:, 6],
                            measurements[:, 7], measurements[:, 5], controls[:, 9], controls[:, 3]])


class ObservationReader:
    def __init__(self, registry):
        self.registry = registry
        self.identities = IdentityStore(registry)

    def _raw(self, path):
        arrays = self.registry.trusted_npz(path, ('t_seconds', 'XMEAS', 'XMV'))
        t, x, u = (arrays[k] for k in ('t_seconds', 'XMEAS', 'XMV'))
        require(t.ndim == 1 and np.array_equal(t, np.arange(len(t))) and
                x.shape == (len(t), 41) and u.shape == (len(t), 12),
                'TIME_GRID_ERROR', 'complete raw 1-second 41/12-column trajectory required')
        require(np.isfinite(x).all() and np.isfinite(u).all(), 'NONFINITE_INPUT', 'raw observations')
        return t, x, u

    def read(self, data_ref, task, *, as_of, window=None):
        require(isinstance(as_of, (int, float)) and np.isfinite(as_of) and as_of >= 0,
                'INPUT_SCHEMA_ERROR', 'invalid server as_of')
        require(task in self.registry.catalog['contracts'], 'CONTRACT_MISMATCH', 'unknown task')
        contract = self.registry.catalog['contracts'][task]
        identity, record, folder, path = self.identities.resolve(data_ref)
        require(identity.dataset_id in contract['datasets'], 'DATASET_SCOPE_UNVERIFIED', task)
        sources = [path, folder + '/manifest.json', 'artifacts/d3/dataset/split_plan.json'
                   if identity.dataset_id == 'D3' else 'artifacts/d5_1_1/data_log.json']
        sources.extend(('docs/research/D4_VARIABLE_MAPPING.md',
                        'src/causalverse/data/preprocessing.py', 'src/causalverse/causal/dynamic.py'))
        if identity.dataset_id == 'D511':
            sources.extend(('artifacts/d5_1_1/protocol.json', 'experiments/d511_data.py'))
        if task == 'D512':
            sources.append('artifacts/d5_1_2/protocol.json')
        t, x, u = self._raw(path)
        # Only public observation arrays are materialized; hidden arrays are never indexed.
        mask = t <= as_of
        t, x, u = t[mask], x[mask], u[mask]
        command = None
        action = None
        if task == 'D3':
            mask = (t >= 1800) & (t % 180 == 0)
            t, values = t[mask], x[mask]
            processed = f'artifacts/d3/dataset/processed/{record["dataset_run_id"]}.npz'
            saved = self.registry.trusted_npz(processed, ('t_seconds', 'XMEAS'))
            visible = saved['t_seconds'] <= as_of
            require(np.array_equal(t, saved['t_seconds'][visible]) and
                    np.array_equal(values, saved['XMEAS'][visible]), 'CACHE_MISMATCH', 'raw/processed')
            sources.append(processed)
        elif task in ('D4', 'D512'):
            require(identity.dataset_id == 'D3', 'DATASET_SCOPE_UNVERIFIED', 'external reconstruction deferred')
            mask = t % 10 == 0
            t, values = t[mask], seven(x[mask], u[mask])
            cached_path = f'artifacts/d4/observations/{record["dataset_run_id"]}.npz'
            cached = self.registry.trusted_npz(cached_path, ('t_seconds', 'values'))
            visible = cached['t_seconds'] <= as_of
            require(np.array_equal(t, cached['t_seconds'][visible]) and
                    np.array_equal(values, cached['values'][visible]), 'CACHE_MISMATCH', 'raw/D4 cache')
            sources.append(cached_path)
            if task == 'D512':
                require(window in (180, 600, 1800), 'WINDOW_UNSUPPORTED', 'fixed windows only')
                require(as_of >= 3600 + window, 'WINDOW_INCOMPLETE', 'half-open window clock not complete')
                values = values[:, [0, 1, 2, 5]].copy()
                mask = (t >= 3600) & (t < 3600 + window)
                t, values = t[mask], values[mask]
                require(len(t) == window // 10, 'WINDOW_INCOMPLETE', 'missing samples')
        else:
            require(as_of >= 5400, 'WINDOW_INCOMPLETE', '5400 action origin not reached')
            t, values = np.arange(5340, 5400, 10), seven(x[5340:5400:10], u[5340:5400:10])
            cached_path = f'artifacts/d5_1_1/observed/{identity.branch_id}.npz'
            saved = self.registry.trusted_npz(cached_path, ('history', 'command'))
            command = float(saved['command'])
            # The raw command_before at 5400 is pre-scheduling; XMV[5390] is not.
            before = self.registry.trusted_npz(path, ('command_before',))['command_before'][5400, 9]
            require(command == record['command_before'] == before and
                    np.array_equal(values, saved['history']), 'COMMAND_MISMATCH', 'pre-action command/history')
            sources.append(cached_path)
            action = (5400, (0, 1, 5), 120, (10, 30, 60, 120, 300, 600))
            # Parent/snapshot alone is insufficient: compare all public pre-origin history in all three arms.
            parent_history = stable_hash(seven(x[:5400], u[:5400]))
            peers = [(name, r) for name, r in self.identities.d511.items()
                     if r['snapshot_id'] == record['snapshot_id'] and r['split'] == record['split']]
            require(sorted(r['delta'] for _, r in peers) == [0, 1, 5], 'IDENTITY_ERROR', 'three arms required')
            for name, peer in peers:
                other, _, other_folder, other_path = self.identities.resolve('D511:' + name)
                same_identity(identity, other, paired=True)
                _, px, pu = self._raw(other_path)
                require(stable_hash(seven(px[:5400], pu[:5400])) == parent_history and
                        peer['command_before'] == command, 'PARENT_HISTORY_MISMATCH', name)
                sources.extend((other_path, other_folder + '/manifest.json'))
        if task != 'D512':
            require(window is None, 'WINDOW_UNSUPPORTED', 'window only applies to D512')
        validate_observations(t, values, contract['columns'], contract['units'], contract, as_of)
        require(len(t) > 0, 'WINDOW_INCOMPLETE', 'no eligible samples')
        values = values.copy()
        values.setflags(write=False)
        context = ObservationContext(uuid.uuid4().hex, identity.dataset_id, identity.run_id, identity.split,
                                     identity.branch_id, identity.parent_run_id, identity.snapshot_id,
                                     as_of, tuple(t.tolist()), window, action, tuple(contract['columns']),
                                     tuple(contract['units']), values, command,
                                     self.identities.source_digest(sources), '', stable_hash(contract))
        return replace(context, input_hash=stable_hash(context_payload(context)))

    def admit(self, request, context):
        require(type(request) is InferenceRequest and type(context) is ObservationContext,
                'INPUT_SCHEMA_ERROR', 'separate online request/context types required')
        entry = self.registry.entry(request.model_id, request.task)
        validate_request(request, context, entry)
        contract = self.registry.catalog['contracts'][request.task]
        require(context.contract_hash == stable_hash(contract) and
                context.input_hash == stable_hash(context_payload(context)), 'CONTEXT_MISMATCH', 'modified context')
        require(entry['input_contract'].get('window') == context.window,
                'CONTRACT_MISMATCH', 'model window differs')
        # Re-resolve from trusted sources; fabricated contexts cannot enter future runtime.
        name = context.branch_id if context.dataset_id == 'D511' else next(
            (name for name in self.identities.d3 if
             self.registry.trusted_json(f'artifacts/d3/dataset/raw/{name}/manifest.json')['run_id'] == context.run_id), None)
        require(name is not None, 'IDENTITY_ERROR', 'unknown engine run')
        fresh = self.read(context.dataset_id + ':' + name, request.task, as_of=context.as_of, window=context.window)
        require(fresh.input_hash == context.input_hash, 'CONTEXT_MISMATCH', 'context differs from source')
        self.registry.load(request.model_id, request.task)
        return {'status': 'READY', 'reason': 'ADMISSION_ONLY_NO_INFERENCE', 'context_id': context.context_id}
