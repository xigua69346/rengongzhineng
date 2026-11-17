"""Frozen numerical algorithms with a separately admitted LIVE input contract."""
import time
import numpy as np
from causalverse.ai_runtime.registry import Registry
from causalverse.data.preprocessing import Standardizer
from causalverse.detection.pca import PCADetector
from causalverse.detection.threshold import ThresholdDetector
from .contracts import digest,X_COLUMNS

class DetectionBridge:
    def __init__(self):
        registry=Registry();p=registry.load('d3.pca','D3');registry.load('d3.threshold','D3')
        self.scaler=Standardizer();self.pca=PCADetector();self.threshold=ThresholdDetector()
        self.scaler.mean,self.scaler.scale,self.scaler.constant=p['mean'],p['scale'],p['constant']
        self.pca.center,self.pca.components,self.pca.eigenvalues=p['pca_center'],p['components'],p['eigenvalues']
        self.pca.explained_variance,self.pca.ratio=p['explained_variance'],p['explained_ratio']
        self.threshold.center,self.threshold.width=p['threshold_center'],p['threshold_width']
        self.limits=registry.trusted_json('artifacts/d3/detection/model_manifest.json')['limits']
        self.version=registry.entry('d3.pca','D3')['model_version']
        self.model_hash=registry.entry('d3.pca','D3')['parameter_sha256']

    def score(self,values,times,episode):
        start=time.perf_counter();x=np.asarray(values,dtype=np.float64);t=np.asarray(times)
        if x.shape!=(len(t),41) or not len(t) or not np.isfinite(x).all():raise ValueError('DETECTION_INPUT')
        if not np.all((t>=1800)&(t%180==0)) or not np.all(np.diff(t)>0):raise ValueError('DETECTION_GRID')
        z=self.scaler.transform(x);a=self.pca.scores(z)
        a['threshold_score']=self.threshold.score(z);a['threshold_contribution']=self.threshold.contributions(z)
        a['pred_T2']=a['T2']>self.limits['T2'];a['pred_SPE']=a['SPE']>self.limits['SPE']
        a['pred_PCA']=a['pred_T2']|a['pred_SPE'];a['pred_Threshold']=a['threshold_score']>self.limits['Threshold']
        payload=dict(dtype=str(x.dtype),shape=list(x.shape),columns=X_COLUMNS,times=t.tolist(),values=x.tolist())
        return dict(status='INFERRED',applicability='LIVE_SHADOW_NOT_VALIDATED_ONLINE_ALARM_PERFORMANCE',
            episode_id=episode,model_id=['d3.pca','d3.threshold'],model_version=self.version,model_hash=self.model_hash,
            inference_id=digest(dict(episode_id=episode,input_hash=digest(payload),model_hash=self.model_hash)),
            observation_payload_hash=digest(payload),limits=self.limits,observation_time=t.tolist(),
            arrays={k:v.tolist() for k,v in a.items()},elapsed_ms=(time.perf_counter()-start)*1000,
            optimization_allowed=False)
