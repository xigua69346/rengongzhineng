import json
from pathlib import Path
import numpy as np

def load_runs(root,split):
    root=Path(root); plan=json.loads((root/'split_plan.json').read_text())
    runs=[]
    for spec in plan['runs']:
        if spec['split']!=split: continue
        with np.load(root/'processed'/f"{spec['dataset_run_id']}.npz") as d:
            runs.append((spec,{k:d[k] for k in d.files}))
    return runs
