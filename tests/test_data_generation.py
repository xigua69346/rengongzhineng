import json
from causalverse.data.manifest import freeze_plan
from causalverse.data.generator import generate_one

def test_split_freeze_and_no_leakage(tmp_path):
    p=freeze_plan(tmp_path/'split_plan.json')
    assert len(p['runs'])==200
    assert len({r['seed'] for r in p['runs']})==200
    for split,n in [('train',20),('validation',10),('test',20)]:
        for f in (0,4,11,14): assert sum(r['split']==split and r['fault_id']==f for r in p['runs'])==n

def test_real_generation(tmp_path):
    p=dict(horizon_seconds=181,onset_seconds=60,fault_duration_seconds=121,warmup_seconds=0,sample_seconds=180)
    (tmp_path/'split_plan.json').write_text(json.dumps(p))
    s=dict(dataset_run_id='unit',split='train',fault_id=4,seed=431)
    result=generate_one(tmp_path,p,s)
    assert result['status']=='complete'
    m=json.loads((tmp_path/'raw/unit/manifest.json').read_text())
    assert m['fault_duration_seconds']==121 and m['backend']=='python'
