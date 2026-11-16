"""Separate online observations, requests and offline evaluation contracts."""
from dataclasses import dataclass
import numpy as np


class AdmissionError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f'{code}: {detail}')


def require(condition, code, detail):
    if not condition:
        raise AdmissionError(code, detail)


@dataclass(frozen=True)
class ObservationContext:
    context_id: str
    dataset_id: str
    run_id: str
    split: str
    branch_id: str | None
    parent_run_id: str | None
    snapshot_id: str | None
    as_of: float
    observation_time: tuple
    window: int | None
    action_contract: tuple | None
    columns: tuple
    units: tuple
    values: np.ndarray
    command_before: float | None
    source_hash: str
    input_hash: str
    contract_hash: str


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    context_id: str
    model_id: str
    model_version: str
    task: str
    action: int | None = None
    duration_seconds: int = 120
    origin: int = 5400
    horizons: tuple = (10, 30, 60, 120, 300, 600)

    @classmethod
    def from_payload(cls, payload):
        require(isinstance(payload, dict), 'INPUT_SCHEMA_ERROR', 'request must be an object')
        require(not (set(payload) - set(cls.__dataclass_fields__)),
                'INPUT_SCHEMA_ERROR', 'unknown/forbidden online fields')
        try:
            return cls(**payload)
        except TypeError as exc:
            raise AdmissionError('INPUT_SCHEMA_ERROR', str(exc)) from exc


@dataclass(frozen=True)
class EvaluationContext:
    evaluation_id: str
    context_id: str
    reference_id: str
    truth: object
    mode: str = 'offline_only'


def validate_observations(times, values, columns, units, contract, as_of):
    require(np.isfinite(as_of) and as_of >= 0, 'INPUT_SCHEMA_ERROR', 'invalid as_of')
    require(tuple(columns) == tuple(contract['columns']), 'COLUMN_ORDER_ERROR', 'exact columns required')
    require(tuple(units) == tuple(contract['units']), 'UNIT_ERROR', 'units differ')
    t = np.asarray(times)
    x = np.asarray(values)
    require(t.ndim == 1 and x.shape == (len(t), len(columns)), 'SHAPE_ERROR', 'observation shape')
    require(x.dtype.kind == 'f' and np.isfinite(x).all() and np.isfinite(t).all(),
            'NONFINITE_INPUT', 'finite floating observations required')
    require(np.all(t <= as_of), 'FUTURE_INPUT', 'observation_time exceeds as_of')
    require(np.all(np.diff(t) == contract['grid_seconds']) and
            np.all(t % contract['grid_seconds'] == 0), 'TIME_GRID_ERROR', 'incorrect sample grid')


def validate_request(request, context, entry):
    require(type(request) is InferenceRequest and type(context) is ObservationContext,
            'INPUT_SCHEMA_ERROR', 'online types required; evaluation is separate')
    require(request.context_id == context.context_id, 'CONTEXT_MISMATCH', 'request/context')
    require(request.model_id == entry['model_id'] and request.model_version == entry['model_version'],
            'MODEL_VERSION_ERROR', 'explicit model/version required')
    require(request.task == entry['input_contract']['task'], 'CONTRACT_MISMATCH', 'task differs')
    require(context.dataset_id in entry['supported_scope']['datasets'],
            'DATASET_SCOPE_UNVERIFIED', 'dataset not supported')
    if request.task == 'D511':
        require(request.action in (0, 1, 5) and type(request.action) is int and
                request.duration_seconds == 120 and request.origin == 5400 and
                tuple(request.horizons) == (10, 30, 60, 120, 300, 600),
                'ACTION_UNSUPPORTED', 'frozen action/origin/duration/horizons required')
        require(context.command_before is not None and 0 <= context.command_before + request.action <= 100,
                'COMMAND_SATURATION', 'command plus action outside [0,100]')
