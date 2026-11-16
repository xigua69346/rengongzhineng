"""Resolve logical data references exclusively from frozen manifests and protocols."""
from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from .contracts import require
from .provenance import stable_hash


@dataclass(frozen=True)
class DataIdentity:
    dataset_id: str
    run_id: str
    split: str
    branch_id: str | None
    parent_run_id: str | None
    snapshot_id: str | None


def same_identity(left, right, *, paired=False):
    fields = ('dataset_id', 'split', 'parent_run_id', 'snapshot_id') if paired else tuple(DataIdentity.__dataclass_fields__)
    for field in fields:
        require(getattr(left, field) == getattr(right, field), 'CONTEXT_MISMATCH', field)
    if paired:
        require(left.parent_run_id is not None and left.snapshot_id is not None,
                'CONTEXT_MISMATCH', 'pair requires recorded parent and snapshot plus history digest')


class IdentityStore:
    def __init__(self, registry):
        self.registry = registry
        self.plan = registry.trusted_json('artifacts/d3/dataset/split_plan.json')
        self.protocol = registry.trusted_json('artifacts/d5_1_1/protocol.json')
        self.d3 = {r['dataset_run_id']: r for r in self.plan['runs']}
        records = registry.trusted_json('artifacts/d5_1_1/data_log.json')['runs']
        self.d511 = {PurePosixPath(r['folder'].replace('\\', '/')).name: r for r in records}
        require(len(self.d511) == len(records), 'IDENTITY_ERROR', 'duplicate branches')

    def resolve(self, data_ref):
        require(isinstance(data_ref, str) and re.fullmatch(r'(D3|D511):[A-Za-z0-9_]+', data_ref),
                'PATH_REJECTED', 'use logical dataset:registered-run reference')
        dataset, name = data_ref.split(':')
        records = self.d3 if dataset == 'D3' else self.d511
        require(name in records, 'DATA_UNKNOWN', data_ref)
        record = records[name]
        folder = f'artifacts/d3/dataset/raw/{name}' if dataset == 'D3' else record['folder'].replace('\\', '/')
        manifest = self.registry.trusted_json(folder + '/manifest.json')
        if dataset == 'D3':
            require(manifest['dataset_run_id'] == name and manifest['split'] == record['split'] and
                    manifest['seed'] == record['seed'] and manifest['dataset_plan_sha256'] ==
                    self.registry.baseline['artifacts/d3/dataset/split_plan.json']['sha256'],
                    'IDENTITY_ERROR', 'D3 manifest/plan differ')
        else:
            require(record['seed'] in self.protocol['seeds'][record['split']] and
                    manifest['random_seed'] == record['seed'] and record['delta'] in self.protocol['actions'],
                    'IDENTITY_ERROR', 'branch/protocol differ')
        trajectory = folder + '/trajectory.npz'
        require(manifest['sha256']['trajectory.npz'] == self.registry.baseline[trajectory]['sha256'],
                'IDENTITY_ERROR', 'trajectory manifest hash differs')
        identity = DataIdentity(dataset, manifest['run_id'], record['split'],
                                name if dataset == 'D511' else None, manifest['parent_run_id'],
                                record.get('snapshot_id'))
        return identity, record, folder, trajectory

    def source_digest(self, paths):
        return stable_hash({p: self.registry.baseline[p]['sha256'] for p in sorted(set(paths))})
