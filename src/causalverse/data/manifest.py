import hashlib
import json
from pathlib import Path

def write_json(path, value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def freeze_plan(path):
    path=Path(path)
    if path.exists():
        raise FileExistsError('Plan already frozen')
    runs=[]
    for split,base,n in [('train',100000,20),('validation',200000,10),('test',300000,20)]:
        for fault in (0,4,11,14):
            for i in range(n):
                runs.append(dict(dataset_run_id=f'{split}_f{fault:02d}_{i:02d}',split=split,fault_id=fault,seed=base+fault*1000+i))
    plan=dict(schema_version=1,horizon_seconds=14400,warmup_seconds=1800,onset_seconds=3600,sample_seconds=180,
              fault_duration_seconds=10800,measurement_ids=list(range(1,42)),control_ids=list(range(1,13)),
              runs=runs,protocol=dict(pca_variance=0.90,threshold_quantile=0.99,statistic_quantile=0.995,
              calibration='normal validation only',delay='first positive after onset; undetected is null',
              pilot_excluded=True))
    assert len({r['seed'] for r in runs})==len(runs)
    write_json(path,plan)
    return plan
