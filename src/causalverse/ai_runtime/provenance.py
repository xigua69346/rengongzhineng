"""Deterministic typed hashes and append-only admission traces."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
import numpy as np


def canonical(value):
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, np.ndarray):
        if value.dtype.kind not in 'biuf':
            raise TypeError('Only numeric observation/parameter arrays can be hashed')
        data = np.ascontiguousarray(value)
        counts = {}
        if data.dtype.kind == 'f':
            nan = np.isnan(data)
            counts = {'NaN': int(nan.sum()), '+Inf': int(np.isposinf(data).sum()),
                      '-Inf': int(np.isneginf(data).sum())}
            if nan.any():
                data = data.copy()
                data[nan] = np.nan  # Canonicalize different NaN payload bits.
        return {'$array': {'dtype': value.dtype.str, 'shape': list(value.shape),
                           'encoding': 'C-order-hex-v1', 'data': data.tobytes().hex(),
                           'nonfinite': counts}}
    if isinstance(value, np.generic):
        return canonical(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return {'$float': 'NaN' if np.isnan(value) else '+Inf' if value > 0 else '-Inf'}
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Unsupported hash value: {type(value).__name__}')


def stable_hash(value):
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def context_payload(context):
    return {k: v for k, v in asdict(context).items() if k not in ('context_id', 'input_hash')}


def trace_admission(operation, *, request_id, model_id, output_dir, context=None, entry=None):
    """Record successful, waiting and rejected admission; operation never performs inference."""
    start = time.perf_counter()
    trace = dict(inference_id=uuid.uuid4().hex, request_id=request_id,
                 context_id=getattr(context, 'context_id', None), model_id=model_id,
                 model_hash=entry['parameter_sha256'] if entry else None,
                 source_hash=getattr(context, 'source_hash', None),
                 input_hash=getattr(context, 'input_hash', None),
                 contract_hash=getattr(context, 'contract_hash', None),
                 created_at=datetime.now(timezone.utc).isoformat(), cache_hit=False)
    try:
        result = operation()
        trace.update(status='READY', reason='ADMISSION_ONLY_NO_INFERENCE')
    except Exception as exc:
        result = None
        trace.update(status='WAITING' if getattr(exc, 'code', '') == 'WINDOW_INCOMPLETE' else 'REJECTED',
                     reason=str(exc))
    trace['elapsed_ms'] = (time.perf_counter() - start) * 1000
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (trace['inference_id'] + '.json')).open('x', encoding='utf-8') as f:
        json.dump(trace, f, ensure_ascii=False, indent=2, allow_nan=False)
    return result, trace
