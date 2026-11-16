"""Frozen finite-horizon Action/Delta inference; comparison only after computation."""
import json
from pathlib import Path
import time
import numpy as np
from .contracts import InferenceRequest,AdmissionError,require,validate_request,validate_observations
from .registry import Registry,file_hash
from .observation_reader import ObservationReader
from .provenance import canonical,stable_hash,trace_admission
from .detection_runtime import observation_payload_hash
from .calibration_loader import CalibrationLoader
from .support_runtime import SupportRuntime,restore_members

HORIZONS=(10,30,60,120,300,600)


def validate_prediction_contract(context,entry,actions,duration,origin,horizons):
    require(context.command_before is not None,'COMMAND_MISSING','explicit original pre-action command required')
    require(tuple(context.observation_time)==tuple(range(5340,5400,10)),
            'CONTRACT_MISMATCH','original six history times required')
    validate_observations(context.observation_time,context.values,context.columns,context.units,
                          entry['input_contract'],context.as_of)
    require(isinstance(actions,(tuple,list)) and len(actions)>0 and len(set(actions))==len(actions),
            'ACTION_UNSUPPORTED','nonempty distinct frozen actions required')
    for action in actions:
        validate_request(InferenceRequest('prediction-admission',context.context_id,entry['model_id'],
                         entry['model_version'],'D511',action=action,duration_seconds=duration,
                         origin=origin,horizons=tuple(horizons)),context,entry)


class PredictionRuntime:
    def __init__(self,evidence_dir,registry=None):
        self.evidence_dir=Path(evidence_dir);self.registry=Registry() if registry is None else registry
        self.reader=ObservationReader(self.registry);self.calibration=CalibrationLoader(self.registry)
        self.support=SupportRuntime(self.registry)
        self.parameters={k:self.registry.load('d511.'+k,'D511') for k in ('action','delta')}
        self.models={k:restore_members(p,k) for k,p in self.parameters.items()}
        for p in self.parameters.values():require(p['bootstrap_seeds'].shape==(20,20),'MEMBER_PARAMETER_MISSING','bootstrap members')

    def _prepare(self,data_ref,kind,actions,duration,origin,horizons,as_of):
        require(kind in self.models,'MODEL_UNKNOWN','Action/Delta only')
        context=self.reader.read(data_ref,'D511',as_of=as_of)
        entry=self.registry.entry('d511.'+kind,'D511')
        validate_prediction_contract(context,entry,actions,duration,origin,horizons)
        # Revalidate frozen byte identities even when immutable parameter objects are reused.
        for mid in ('d511.'+kind,'d511.support','d511.candidate_support','d511.calibration_'+kind):
            e=self.registry.entry(mid);self.registry.read_bytes(e['parameter_path'],e['parameter_sha256'])
        return context,entry

    def predict(self,data_ref,*,kind,as_of=5400,actions=(0,1,5),duration=120,origin=5400,horizons=HORIZONS,request_id):
        start=time.perf_counter()
        prepared,admission=trace_admission(lambda:self._prepare(data_ref,kind,actions,duration,origin,horizons,as_of),
            request_id=request_id,model_id='d511.'+kind,output_dir=self.evidence_dir/'admission')
        result=dict(admission,phase='prediction',execution_mode='recomputed_frozen',data_ref=data_ref,kind=kind,
            as_of=as_of,origin=origin,actions=list(actions),horizons=list(horizons),targets=['T9','C21','P7'],
            records=[],arrays={},computation_status='NOT_COMPUTED',contract_valid=False,
            support_status='NOT_EVALUATED',uncertainty_status='NOT_EVALUATED',optimization_allowed=False)
        if prepared is not None:
            context,entry=prepared
            try:
                rows=[];members_all=[];means_all=[];low=[];high=[];candidate_members=[];candidate_means=[];stds=[]
                for delta in actions:
                    members=np.array([m.predict(context.values,delta,context.command_before) for m in self.models[kind]])
                    require(members.shape==(20,6,3) and np.isfinite(members).all(),'MEMBER_OUTPUT_INVALID','twenty finite members')
                    mean=members.mean(0);bounds=self.calibration.bounds(mean,kind,delta)
                    audit=self.support.evaluate(context.values,delta,context.command_before,kind,members)
                    too_wide=bool(np.any(bounds['full_width']>self.calibration.protocol['width_limits']))
                    rows.append(dict(delta=delta,computation_status='COMPLETED',contract_valid=True,
                        support_status=audit['support_status'],support_reasons=audit['reasons'],base_support=audit['base_support'],
                        horizon_checks=audit['horizon_checks'],member_disagreement=audit['member_disagreement'],
                        candidate_normalized_range=audit['candidate_normalized_range'],candidate_audit_status='AUDIT_ONLY',
                        recursive_spectral_radius_status=audit['recursive_spectral_radius_status'],
                        uncertainty_status='INTERVAL_TOO_WIDE' if too_wide else 'WIDTH_WITHIN_LIMITS_ONLY',
                        uncertainty_reasons=['joint_interval_too_wide'] if too_wide else [],
                        coverage_status='NOT_EVALUATED_ONLINE',full_width=bounds['full_width'].tolist(),
                        joint_radius=bounds['joint'],actionwise_radius_audit_only=bounds['actionwise_audit_only'],optimization_allowed=False))
                    members_all.append(members);means_all.append(mean);low.append(bounds['lower']);high.append(bounds['upper'])
                    candidate_members.append(audit['candidate_members']);candidate_means.append(audit['candidate_means']);stds.append(audit['member_std'])
                result.update(status='INFERRED',reason='FROZEN_PREDICTION_NOT_ACTION_AUTHORIZATION',
                    computation_status='COMPLETED',contract_valid=True,support_status='PER_ACTION_SEE_RECORDS',
                    uncertainty_status='PER_ACTION_SEE_RECORDS',records=rows,
                    model_id=entry['model_id'],model_version=entry['model_version'],model_hash=entry['parameter_sha256'],
                    context_id=context.context_id,run_id=context.run_id,split=context.split,parent_run_id=context.parent_run_id,
                    snapshot_id=context.snapshot_id,columns=context.columns,observation_time=context.observation_time,
                    command_before=context.command_before,source_hash=context.source_hash,
                    observation_payload_hash=observation_payload_hash(context),p0_01_context_input_hash=context.input_hash,
                    contract_hash=context.contract_hash,
                    parameter_hashes={mid:self.registry.entry(mid)['parameter_sha256'] for mid in
                        ('d511.'+kind,'d511.support','d511.candidate_support','d511.calibration_'+kind)},
                    bootstrap_seeds=self.parameters[kind]['bootstrap_seeds'].tolist(),
                    arrays=dict(members=np.array(members_all),mean=np.array(means_all),joint_lower=np.array(low),joint_upper=np.array(high),
                        member_std=np.array(stds),candidate_members=np.array(candidate_members),candidate_means=np.array(candidate_means)))
                result['inference_identity_hash']=stable_hash({k:result[k] for k in ('data_ref','as_of','actions',
                    'command_before','observation_payload_hash','source_hash','parameter_hashes','contract_hash')})
            except Exception as exc:
                result.update(status='FAILED',computation_status='FAILED',reason=f'{type(exc).__name__}: {exc}',arrays={})
        result['elapsed_ms']=(time.perf_counter()-start)*1000
        folder=self.evidence_dir/result['inference_id'];folder.mkdir(parents=True,exist_ok=False)
        if result['arrays']:
            with (folder/'result.npz').open('xb') as f:np.savez_compressed(f,**result['arrays'])
            result['arrays_file_sha256']=file_hash(folder/'result.npz')
        with (folder/'result.json').open('x',encoding='utf-8') as f:
            json.dump(canonical({k:v for k,v in result.items() if k!='arrays'}),f,ensure_ascii=False,indent=2,allow_nan=False)
        return result

    def compare_archive(self,result):
        require(result['status']=='INFERRED','COMPARISON_REJECTED','computed result required')
        _,record,_,_=self.reader.identities.resolve(result['data_ref']);kind=result['kind']
        comparison=dict(status='UNAVAILABLE',inference_id=result['inference_id'],model_hash=result['model_hash'],rows=[],rtol=1e-12,atol=1e-12)
        try:
            z=self.registry.trusted_npz(f'artifacts/d5_1_1/intervals_{kind}_test.npz',
                ('identifiers','horizons','targets','prediction','joint_lower','joint_upper'))
            disagreement=self.registry.trusted_npz(f'artifacts/d5_1_1/predictions_{kind}_test.npz',('disagreement',))['disagreement']
            support=self.registry.trusted_json('artifacts/d5_1_1/support_results.json')
            candidates=self.registry.trusted_json('artifacts/d5_1_1/candidate_disagreement.json')['rows']
        except AdmissionError as exc:
            comparison.update(status='UNAVAILABLE' if exc.code=='FILE_MISSING' else 'REJECTED',reason=str(exc));return comparison
        require(tuple(z['horizons'])==HORIZONS and list(z['targets'])==['T9','C21','P7'], 'CONTRACT_MISMATCH','reference horizons/targets')
        for j,delta in enumerate(result['actions']):
            key=(record['seed'],record['mechanism'],delta)
            ids=np.flatnonzero(np.all(z['identifiers']==key,axis=1));require(len(ids)==1,'CONTEXT_MISMATCH','reference identity')
            i=int(ids[0]);ref=candidates[i]['models'][kind];row=dict(delta=delta,identifiers=list(key),metrics={})
            pairs={'mean':z['prediction'][i],'joint_lower':z['joint_lower'][i],'joint_upper':z['joint_upper'][i],
                   'candidate_means':np.array(ref['candidate_means'])}
            for name,expected in pairs.items():
                actual=result['arrays'][name][j]
                row['metrics'][name]=dict(max_absolute_error=float(np.max(np.abs(actual-expected))),
                    matched=bool(np.allclose(actual,expected,rtol=1e-12,atol=1e-12)))
                if not row['metrics'][name]['matched']:row['metrics'][name].update(actual=actual.tolist(),reference=expected.tolist())
            current=result['records'][j];base=support[i]['checks']['by_model'][kind]
            row.update(member_disagreement_error=abs(current['member_disagreement']-float(disagreement[i])),
                candidate_range_error=abs(current['candidate_normalized_range']-ref['normalized_range']),
                base_support_matched=current['base_support']==base,
                support_matched=(current['support_status']=='SUPPORTED')==ref['supported'] and current['support_reasons']==ref['reasons'])
            row['matched']=all(m['matched'] for m in row['metrics'].values()) and row['base_support_matched'] and row['support_matched'] and \
                bool(np.isclose(current['member_disagreement'],disagreement[i],rtol=1e-12,atol=1e-12)) and \
                bool(np.isclose(current['candidate_normalized_range'],ref['normalized_range'],rtol=1e-12,atol=1e-12))
            comparison['rows'].append(row)
        comparison['status']='MATCHED' if all(r['matched'] for r in comparison['rows']) else 'MISMATCH'
        return comparison
