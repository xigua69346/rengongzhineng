import json,os
from pathlib import Path
import numpy as np
import pytest
from causalverse.autonomy.detection_bridge import DetectionBridge
from causalverse.autonomy.events import Events
from causalverse.ai_runtime.registry import Registry
from causalverse.ai_runtime.identity import IdentityStore
from causalverse.ai_runtime.detection_runtime import DetectionRuntime,NUMERIC_KEYS,ALARM_KEYS

OUT=Path(os.environ['S3_ACCEPTANCE'])

def test_all_80_p0_replays(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('TRAINING_FORBIDDEN')
    for path in ['causalverse.data.preprocessing.Standardizer.fit','causalverse.detection.pca.PCADetector.fit','causalverse.detection.threshold.ThresholdDetector.fit','causalverse.detection.statistics.control_limit']:
        monkeypatch.setattr(path,forbidden)
    registry=Registry();bridge=DetectionBridge();p0=DetectionRuntime(OUT/'p0_replay',registry)
    identities=IdentityStore(registry);records=[]
    for name,record in identities.d3.items():
        if record['split']!='test':continue
        ref='D3:'+name;context=p0.reader.read(ref,'D3',as_of=14399)
        actual=bridge.score(context.values,context.observation_time,ref)
        original=p0.detect(ref,as_of=14399,request_id=name)
        assert original['status']=='INFERRED'
        assert len(actual['observation_time'])==70
        diffs={}
        for key in NUMERIC_KEYS:
            arr=np.asarray(actual['arrays'][key]);expected=original['arrays'][key]
            np.testing.assert_allclose(arr,expected,rtol=1e-12,atol=1e-12)
            diffs[key]=float(np.max(np.abs(arr-expected)))
        for key in ALARM_KEYS:np.testing.assert_array_equal(actual['arrays'][key],original['arrays'][key])
        assert p0.compare_archive(original)['status']=='MATCHED'
        (OUT/'recomputed_arrays').mkdir(exist_ok=True)
        np.savez_compressed(OUT/'recomputed_arrays'/f'{name}.npz',**actual['arrays'])
        with np.load(Path('artifacts/d3/detection')/f'{name}.npz',allow_pickle=False) as archive:
            truth=archive['y'].astype(bool)
        evaluation={}
        for model in ('PCA','Threshold'):
            prediction=np.asarray(actual['arrays']['pred_'+model],dtype=bool)
            evaluation[model]=dict(false_positive=int(np.sum(prediction&~truth)),false_negative=int(np.sum(~prediction&truth)),
                not_triggered=not bool(prediction.any()),evaluation_mode='OFFLINE_ARCHIVE_LABELS_NOT_ONLINE_INPUT')
        records.append(dict(run=name,samples=70,max_errors=diffs,boolean_exact=True,p0_archive='MATCHED',offline_evaluation=evaluation))
    assert len(records)==80
    (OUT/'80_run_comparison.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

def test_event_confirmation_deduplication():
    events=Events('e');base=dict(model_version='frozen',arrays=dict(pred_PCA=[True],pred_Threshold=[False],SPE_contribution=[[1]*41]),observation_time=[1800])
    first=events.update(base);assert first['status']=='CANDIDATE'
    base['observation_time']=[1980];second=events.update(base)
    assert second['status']=='CONFIRMED' and second['event_id']==first['event_id']
    base['arrays']['pred_PCA']=[False];assert events.update(base)['status']=='CLEARED'
    assert events.update(base)['status']=='NOT_TRIGGERED'

@pytest.mark.parametrize('times',[[0],[1801],[1980,1800]])
def test_bad_grid(times):
    with pytest.raises(ValueError):DetectionBridge().score(np.zeros((len(times),41)),times,'e')
