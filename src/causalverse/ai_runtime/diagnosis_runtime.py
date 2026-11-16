"""Frozen D5.1.2 mechanisms. No fit, selection, calibration, archived feature input or simulation."""
import json
from pathlib import Path
import time
import numpy as np
from scipy.special import softmax
from causalverse.causal.dynamic import MechanismEvidence, static_features, residual_features
from causalverse.decision.mechanism import (CLASSES, SmallVAR, LogisticMechanism, CandidatePolicy,
                                            simple_features, conservative_candidates)
from .contracts import AdmissionError, InferenceRequest, require, validate_request
from .detection_runtime import observation_payload_hash
from .provenance import canonical, stable_hash, trace_admission
from .registry import Registry, file_hash
from .window_contract import WindowReader


def candidate_result(scores, raw_sets):
    rank, expanded=conservative_candidates(scores,raw_sets)
    records=[]
    for order,raw,final in zip(rank,raw_sets,expanded):
        candidates=CLASSES[order[final[order]]].tolist()
        records.append(dict(ranking=CLASSES[order].tolist(),
            raw_candidates=CLASSES[order[raw[order]]].tolist(),candidates=candidates,
            refused=len(candidates)!=1,reason='empty_candidate_outside_known_signature' if not candidates else
                'multiple_candidates' if len(candidates)>1 else 'singleton',
            status='当前观测不足以区分故障原因' if len(candidates)!=1 else '模型内单一候选，非确定因果结论'))
    return rank,expanded,records


def frozen_var(registry, model_id='d512.var4'):
    require(model_id=='d512.var4','CONTRACT_MISMATCH','D4 seven-node research VAR forbidden')
    p=registry.load(model_id,'D512')
    require(p['coef'].shape==(25,4) and int(p['lag'])==6 and float(p['alpha'])==.1,
            'CONTRACT_MISMATCH','original four-node VAR lag6/ridge0.1 required')
    var=SmallVAR()
    for field in ('mean','scale','noise','coef','lag','alpha'):setattr(var,field,p[field])
    var.lag=int(var.lag);var.alpha=float(var.alpha)
    return var


class DiagnosisRuntime:
    def __init__(self,evidence_dir,registry=None):
        self.evidence_dir=Path(evidence_dir)
        self.registry=Registry() if registry is None else registry
        self.windows=WindowReader(self.registry)

    def _prepare(self,refs,kind,window,as_of,origin):
        require(kind in ('static','VAR','logistic'),'METHOD_UNSUPPORTED','original three methods only')
        require(isinstance(refs,(list,tuple)) and len(refs)>0 and len(set(refs))==len(refs),
                'INPUT_SCHEMA_ERROR','nonempty unique logical references required')
        contexts=[self.windows.read(ref,window=window,as_of=as_of,origin=origin) for ref in refs]
        entry=self.registry.entry(f'd512.{kind}.{window}','D512')
        require(entry['input_contract']['columns']==list(contexts[0].columns) and
                entry['input_contract']['window']==window,'CONTRACT_MISMATCH','registered window/schema')
        for c in contexts:
            if c.dataset_id=='D3':
                validate_request(InferenceRequest('diagnosis-admission',c.context_id,entry['model_id'],
                                                  entry['model_version'],'D512'),c,entry)
            # External is an explicit original-protocol audit extension in WindowReader;
            # the immutable P0-01 registry is not silently rewritten to a broader scope.
        params=self.registry.load(entry['model_id'],'D512')
        var=frozen_var(self.registry) if kind=='VAR' else None
        return contexts,entry,params,var

    def diagnose(self,data_refs,*,kind,window,as_of,request_id,origin=3600):
        start=time.perf_counter()
        prepared,admission=trace_admission(lambda:self._prepare(data_refs,kind,window,as_of,origin),
            request_id=request_id,model_id=f'd512.{kind}.{window}',output_dir=self.evidence_dir/'admission')
        result=dict(admission,phase='diagnosis',execution_mode='recomputed_frozen',kind=kind,window=window,
            as_of=as_of,origin=origin,arrays={},records=[],scores_are_calibrated_probabilities=False,
            optimization_allowed=False,comparison_status='NOT_REQUESTED')
        if prepared is not None:
            contexts,entry,p,var=prepared
            try:
                features=np.array([simple_features(c.values) if kind=='logistic' else static_features(c.values)
                    if kind=='static' else residual_features(var,c.values) for c in contexts])
                if kind=='logistic':
                    model=LogisticMechanism()
                    for field in ('mean','scale','coef','iterations','loss'):setattr(model,field,p[field])
                    scores=model.scores(features)
                    raw=1-scores<=p['thresholds']
                else:
                    model=MechanismEvidence()
                    for field in ('center','scale','means','variances','limits'):setattr(model,field,p[field])
                    distances=model.distances(features)
                    scores=softmax(-distances,axis=1)
                    raw=distances<=model.limits
                require(np.isfinite(features).all() and np.isfinite(scores).all(),'NONFINITE_OUTPUT','features/scores')
                rank,expanded,records=candidate_result(scores,raw)
                for ref,c,record,score in zip(data_refs,contexts,records,scores):
                    identity,meta,folder,trajectory=self.windows.reader.identities.resolve(ref)
                    record.update(data_ref=ref,run_id=ref.split(':',1)[1],engine_run_id=c.run_id,
                        dataset_id=c.dataset_id,source_split=c.split,split='test' if c.dataset_id=='D3' else 'external',
                        branch_id=c.branch_id,parent_run_id=c.parent_run_id,snapshot_id=c.snapshot_id,
                        context_id=c.context_id,columns=c.columns,observation_time=c.observation_time,
                        scores=score.tolist(),observation_payload_hash=observation_payload_hash(c),source_hash=c.source_hash,
                        source_file_hash={trajectory:self.registry.baseline[trajectory]['sha256']})
                result.update(status='INFERRED',reason='ORIGINAL_FROZEN_MECHANISM_ALGORITHMS_EXECUTED',records=records,
                    model_id=entry['model_id'],model_hash=entry['parameter_sha256'],model_version=entry['model_version'],
                    contract_hash=stable_hash(entry['input_contract']),classes=CLASSES.tolist(),
                    var_model_reference=self.registry.entry('d512.var4') if kind=='VAR' else None,
                    selection_reference=self.registry.trusted_json('artifacts/d5_1_2/selection.json'),
                    runtime_source_hash={__file__:file_hash(__file__)},
                    arrays=dict(features=features,scores=scores,ranking=CLASSES[rank],
                                raw_candidates=raw,expanded_candidates=expanded,refused=expanded.sum(1)!=1))
                result['inference_identity_hash']=stable_hash({'kind':kind,'window':window,'as_of':as_of,
                    'model_version':entry['model_version'],'inputs':[{k:v for k,v in r.items() if k not in
                    ('context_id','scores','ranking','raw_candidates','candidates','refused','reason','status')} for r in records]})
            except Exception as exc:
                result.update(status='FAILED',reason=f'{type(exc).__name__}: {exc}',arrays={},records=[])
        result['elapsed_ms']=(time.perf_counter()-start)*1000
        folder=self.evidence_dir/result['inference_id'];folder.mkdir(parents=True,exist_ok=False)
        if result['arrays']:
            with (folder/'result.npz').open('xb') as f:np.savez_compressed(f,**result['arrays'])
            result['arrays_file_sha256']=file_hash(folder/'result.npz')
        with (folder/'result.json').open('x',encoding='utf-8') as f:
            json.dump(canonical({k:v for k,v in result.items() if k!='arrays'}),f,ensure_ascii=False,indent=2,allow_nan=False)
        return result

    def compare_archive(self,result):
        require(result['status']=='INFERRED','COMPARISON_REJECTED','computed results required')
        comparison=dict(status='UNAVAILABLE',inference_id=result['inference_id'],kind=result['kind'],window=result['window'],
            model_hash=result['model_hash'],rtol=1e-12,atol=1e-12,records=[])
        try:
            diagnoses=self.registry.trusted_json('artifacts/d5_1_2/diagnoses.json')
            cached=self.registry.trusted_npz(f'artifacts/d5_1_2/features_{result["kind"]}_{result["window"]}.npz',('test_x','external_x'))
        except AdmissionError as exc:
            comparison.update(status='UNAVAILABLE' if exc.code=='FILE_MISSING' else 'REJECTED',reason=str(exc))
            return comparison
        protocol=self.windows.protocol
        orders={'test':[r['dataset_run_id'] for r in protocol['d3_runs'] if r['split']=='test'],
                'external':list(self.windows.external)}
        index={(r['split'],r['run_id'],r['kind'],r['window']):r for r in diagnoses}
        for i,record in enumerate(result['records']):
            ref=index[(record['split'],record['run_id'],result['kind'],result['window'])]
            feature_ref=cached[record['split']+'_x'][orders[record['split']].index(record['run_id'])]
            actual_feature=result['arrays']['features'][i];score=np.asarray(record['scores']);expected=np.asarray(ref['scores'])
            row=dict(run_id=record['run_id'],split=record['split'],columns=record['columns'],
                feature_max_abs_error=float(np.max(np.abs(actual_feature-feature_ref))),
                score_max_abs_error=float(np.max(np.abs(score-expected))),
                feature_matched=bool(np.allclose(actual_feature,feature_ref,rtol=1e-12,atol=1e-12)),
                score_matched=bool(np.allclose(score,expected,rtol=1e-12,atol=1e-12)),
                ranking_matched=record['ranking']==ref['ranking'],candidates_matched=record['candidates']==ref['candidates'],
                refused_matched=record['refused']==ref['refused'],reason_matched=record['reason']==ref['reason'])
            row['matched']=all(row[k] for k in row if k.endswith('_matched'))
            if not row['matched']:
                row.update(feature_actual=actual_feature.tolist(),feature_reference=feature_ref.tolist(),
                    score_actual=score.tolist(),score_reference=ref['scores'],ranking_actual=record['ranking'],
                    ranking_reference=ref['ranking'],candidates_actual=record['candidates'],candidates_reference=ref['candidates'],
                    reason_actual=record['reason'],reason_reference=ref['reason'])
            comparison['records'].append(row)
        comparison['status']='MATCHED' if all(r['matched'] for r in comparison['records']) else 'MISMATCH'
        return comparison
