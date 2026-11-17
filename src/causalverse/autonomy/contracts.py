"""Strict public observation contract; hidden simulator state is never admitted."""
import hashlib
import json
import numpy as np
from tep.constants import MEASUREMENT_UNITS

X_COLUMNS = [f'XMEAS({i})' for i in range(1,42)]
U_COLUMNS = [f'XMV({i})' for i in range(1,13)]
SCHEMA = dict(version='live-tep-1', columns=X_COLUMNS+U_COLUMNS,
              units=list(MEASUREMENT_UNITS)+['% command']*12)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                    allow_nan=False,separators=(',',':')).encode()).hexdigest()

def validate(row, episode_id, expected_seq):
    if set(row)!={'episode_id','observation_id','seq','measurement_time','state_time','wallclock_utc',
                 'measurements','commands','quality','freshness','schema_hash','payload_hash'}:
        raise ValueError('OBSERVATION_FIELDS')
    if row['episode_id']!=episode_id: raise ValueError('EPISODE_MISMATCH')
    if type(row['seq']) is not int or row['seq']!=expected_seq: raise ValueError('SEQUENCE_GAP_OR_REORDER')
    if row['measurement_time']!=expected_seq or row['state_time']!=expected_seq+1:
        raise ValueError('TIME_MISMATCH')
    if np.asarray(row['measurements']).shape!=(41,) or np.asarray(row['commands']).shape!=(12,):
        raise ValueError('CHANNEL_SHAPE')
    if not np.isfinite(row['measurements']+row['commands']).all(): raise ValueError('NONFINITE')
    if row['schema_hash']!=digest(SCHEMA): raise ValueError('SCHEMA_HASH')
    if row['payload_hash']!=digest({k:v for k,v in row.items() if k!='payload_hash'}):
        raise ValueError('PAYLOAD_HASH')
    return row
