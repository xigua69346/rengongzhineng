"""Trusted file identities and defensive parameter loading; never constructs fitted models."""
import hashlib
import io
import json
from pathlib import Path
import re
import numpy as np
from .contracts import require, AdmissionError

ROOT = Path(__file__).resolve().parents[3]


def file_hash(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class Registry:
    def __init__(self, root=ROOT, catalog=None):
        self.root = Path(root).resolve()
        self.catalog = catalog if catalog is not None else json.loads(
            Path(__file__).with_name('model_registry.json').read_text(encoding='utf-8'))
        raw = self.read_bytes('AI_PHASE3_M0_PREPARATION.md', self.catalog['m0_report_sha256'])
        baseline = json.loads(re.search(rb'<!-- M0_BASELINE_JSON_BEGIN -->\s*```json\s*(.*?)```', raw, re.S).group(1))
        self.baseline = {e['path']: e for e in baseline['files']}
        self.entries = {e['model_id']: e for e in self.catalog['models']}
        require(len(self.entries) == len(self.catalog['models']), 'REGISTRY_ERROR', 'duplicate model id')

    def path(self, relative):
        require(isinstance(relative, str) and '\\' not in relative and ':' not in relative,
                'PATH_REJECTED', 'only registered relative POSIX paths')
        p = (self.root / relative).resolve()
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts and p.is_relative_to(self.root),
                'PATH_REJECTED', 'path escapes root')
        return p

    def read_bytes(self, relative, expected):
        p = self.path(relative)
        require(p.is_file(), 'FILE_MISSING', relative)
        data = p.read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, 'MODEL_HASH_MISMATCH', relative)
        return data

    def trusted_bytes(self, relative):
        require(relative in self.baseline, 'PATH_REJECTED', 'source absent from M0')
        return self.read_bytes(relative, self.baseline[relative]['sha256'])

    def trusted_json(self, relative):
        return json.loads(self.trusted_bytes(relative))

    def trusted_npz(self, relative, keys):
        with np.load(io.BytesIO(self.trusted_bytes(relative)), allow_pickle=False) as archive:
            require(set(keys) <= set(archive.files), 'PARAMETER_KEY_MISSING', relative)
            return {k: archive[k].copy() for k in keys}

    def entry(self, model_id, task=None):
        require(model_id in self.entries, 'MODEL_UNKNOWN', str(model_id))
        entry = self.entries[model_id]
        require(task is None or entry['input_contract']['task'] == task,
                'CONTRACT_MISMATCH', 'seven-node research VAR is not four-node classification VAR')
        return entry

    def load(self, model_id, task=None):
        entry = self.entry(model_id, task)
        for source in entry['dependencies']:
            self.read_bytes(source['path'], source['sha256'])
        raw = self.read_bytes(entry['parameter_path'], entry['parameter_sha256'])
        if entry['parameter_path'].endswith('.json'):
            result = json.loads(raw)
            require(result == entry['json_parameters'], 'PARAMETER_VALUE_ERROR', model_id)
            return result
        try:
            with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
                require(set(archive.files) == set(entry['parameter_shapes']), 'PARAMETER_KEY_MISSING', model_id)
                result = {}
                for key, shape in entry['parameter_shapes'].items():
                    value = archive[key]
                    require(list(value.shape) == shape, 'PARAMETER_SHAPE_ERROR', key)
                    require(str(value.dtype) == entry['parameter_dtypes'][key], 'PARAMETER_DTYPE_ERROR', key)
                    require(value.dtype.kind in 'bifu' and np.isfinite(value).all(), 'NONFINITE_PARAMETER', key)
                    if key.endswith(('scale', 'width', 'variances', 'eigenvalues', 'noise')):
                        require(np.all(value > 0), 'PARAMETER_VALUE_ERROR', key)
                    value.setflags(write=False)
                    result[key] = value
                return result
        except AdmissionError:
            raise
        except (OSError, TypeError, ValueError) as exc:
            raise AdmissionError('PARAMETER_FORMAT_ERROR', str(exc)) from exc
