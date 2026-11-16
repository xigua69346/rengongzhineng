"""D3 frozen detection only. Original algorithm calls; archive comparison is explicit and later."""
import json
from pathlib import Path
import time
import numpy as np
from causalverse.data.preprocessing import Standardizer
from causalverse.detection.pca import PCADetector
from causalverse.detection.threshold import ThresholdDetector
from .contracts import AdmissionError, InferenceRequest, require
from .observation_reader import ObservationReader
from .provenance import canonical, stable_hash, trace_admission
from .registry import Registry, file_hash

NUMERIC_KEYS = ('T2', 'SPE', 'projection', 'T2_contribution', 'SPE_contribution',
                'threshold_score', 'threshold_contribution')
ALARM_KEYS = ('pred_T2', 'pred_SPE', 'pred_PCA', 'pred_Threshold')


def observation_payload_hash(context):
    """Only the actual numeric model input, its schema and observation clock."""
    return stable_hash({'XMEAS': context.values, 'columns': context.columns,
                        'observation_time': np.asarray(context.observation_time)})


class DetectionRuntime:
    def __init__(self, evidence_dir, registry=None):
        # Trusted local configuration, never a path field in an online request.
        self.evidence_dir = Path(evidence_dir)
        self.registry = Registry() if registry is None else registry
        self.reader = ObservationReader(self.registry)

    def _prepare(self, data_ref, as_of):
        context = self.reader.read(data_ref, 'D3', as_of=as_of)
        entries = {mid: self.registry.entry(mid, 'D3') for mid in ('d3.pca', 'd3.threshold')}
        for mid, entry in entries.items():
            self.reader.admit(InferenceRequest('detection-admission', context.context_id,
                                              mid, entry['model_version'], 'D3'), context)
        parameters = {mid: self.registry.load(mid, 'D3') for mid in entries}
        require(entries['d3.pca']['parameter_sha256'] == entries['d3.threshold']['parameter_sha256'],
                'MODEL_HASH_MISMATCH', 'D3 scaler/PCA/Threshold must share original parameter file')
        manifest = self.registry.trusted_json('artifacts/d3/detection/model_manifest.json')
        require(all(e['control_limits'] == manifest['limits'] for e in entries.values()),
                'CONTRACT_MISMATCH', 'registered/original control limits differ')
        return context, entries, parameters, manifest

    def detect(self, data_ref, *, as_of, request_id):
        """Persist and return columnar sample results. No archive output is opened here."""
        start = time.perf_counter()
        prepared, admission = trace_admission(
            lambda: self._prepare(data_ref, as_of), request_id=request_id, model_id='d3.pca+d3.threshold',
            output_dir=self.evidence_dir / 'admission')
        result = dict(admission, data_ref=data_ref, as_of=as_of, phase='detection',
                      execution_mode='recomputed_frozen', applicability='D3_FROZEN_PROTOCOL_ONLY',
                      optimization_allowed=False, arrays={}, comparison_status='NOT_REQUESTED',
                      source_file_hash=None, observation_payload_hash=None, inference_identity_hash=None)
        if prepared is not None:
            context, entries, parameters, manifest = prepared
            identity, record, folder, trajectory = self.reader.identities.resolve(data_ref)
            sources = (trajectory, folder + '/manifest.json',
                       f'artifacts/d3/dataset/processed/{record["dataset_run_id"]}.npz',
                       'artifacts/d3/dataset/split_plan.json')
            source_files = {p: self.registry.baseline[p]['sha256'] for p in sources}
            payload_hash = observation_payload_hash(context)
            versions = {mid: e['model_version'] for mid, e in entries.items()}
            hashes = {mid: e['parameter_sha256'] for mid, e in entries.items()}
            code = {__file__: file_hash(__file__)}
            result.update(context_id=context.context_id, dataset_id=context.dataset_id, run_id=context.run_id,
                          split=context.split, branch_id=context.branch_id, parent_run_id=context.parent_run_id,
                          model_id=list(entries), model_version=versions, model_hash=hashes,
                          source_hash=context.source_hash, source_file_hash=source_files,
                          observation_payload_hash=payload_hash, input_hash=payload_hash,
                          p0_01_context_input_hash=context.input_hash, contract_hash=context.contract_hash,
                          columns=context.columns, units=context.units, runtime_source_hash=code,
                          limits=manifest['limits'], limits_reference={
                              'path':'artifacts/d3/detection/model_manifest.json',
                              'sha256':self.registry.baseline['artifacts/d3/detection/model_manifest.json']['sha256']})
            result['inference_identity_hash'] = stable_hash({
                'identity': vars(identity), 'data_ref':data_ref, 'as_of':as_of,
                'observation_payload_hash':payload_hash, 'source_file_hash':source_files,
                'source_hash':context.source_hash, 'models':versions, 'model_hash':hashes,
                'contract_hash':context.contract_hash, 'runtime_source_hash':code})
            score_start = time.perf_counter()
            try:
                p = parameters['d3.pca']
                scaler = Standardizer()
                scaler.mean, scaler.scale, scaler.constant = p['mean'], p['scale'], p['constant']
                pca = PCADetector()
                pca.center, pca.components, pca.eigenvalues = p['pca_center'], p['components'], p['eigenvalues']
                pca.explained_variance, pca.ratio = p['explained_variance'], p['explained_ratio']
                th = parameters['d3.threshold']
                threshold = ThresholdDetector()
                threshold.center, threshold.width = th['threshold_center'], th['threshold_width']
                z = scaler.transform(context.values)
                arrays = dict(pca.scores(z), threshold_score=threshold.score(z),
                              threshold_contribution=threshold.contributions(z),
                              observation_time=np.asarray(context.observation_time))
                require(all(np.isfinite(v).all() for v in arrays.values()),
                        'NONFINITE_OUTPUT', 'frozen detection returned nonfinite values')
                arrays['pred_T2'] = arrays['T2'] > manifest['limits']['T2']
                arrays['pred_SPE'] = arrays['SPE'] > manifest['limits']['SPE']
                arrays['pred_PCA'] = arrays['pred_T2'] | arrays['pred_SPE']
                arrays['pred_Threshold'] = arrays['threshold_score'] > manifest['limits']['Threshold']
                for value in arrays.values():
                    value.setflags(write=False)
                result.update(status='INFERRED', reason='ORIGINAL_FROZEN_ALGORITHMS_EXECUTED', arrays=arrays,
                              sample_count=len(context.values), retained_components=len(pca.components))
            except Exception as exc:
                result.update(status='FAILED', reason=f'{type(exc).__name__}: {exc}', arrays={})
            result['score_elapsed_ms'] = (time.perf_counter() - score_start) * 1000
        result['elapsed_ms'] = (time.perf_counter() - start) * 1000
        destination = self.evidence_dir / result['inference_id']
        destination.mkdir(parents=True, exist_ok=False)
        if result['arrays']:
            with (destination / 'result.npz').open('xb') as f:
                np.savez_compressed(f, **result['arrays'])
            result['arrays_file'] = 'result.npz'
            result['arrays_file_sha256'] = file_hash(destination / 'result.npz')
        metadata = {k:v for k,v in result.items() if k != 'arrays'}
        with (destination / 'result.json').open('x', encoding='utf-8') as f:
            json.dump(canonical(metadata), f, ensure_ascii=False, indent=2, allow_nan=False)
        return result

    def compare_archive(self, result):
        """D3-only retrospective comparison after inference; no labels are requested."""
        require(result.get('status') == 'INFERRED', 'COMPARISON_REJECTED', 'computed result required')
        identity, record, _, _ = self.reader.identities.resolve(result['data_ref'])
        require(identity.run_id == result['run_id'] and identity.split == result['split'],
                'CONTEXT_MISMATCH', 'archive run/split differs')
        path = f'artifacts/d3/detection/{record["dataset_run_id"]}.npz'
        comparison = dict(status='UNAVAILABLE', execution_mode='archive_reference_only', path=path,
                          inference_id=result['inference_id'], model_hash=result['model_hash'],
                          tolerance={'PCA':{'rtol':1e-12,'atol':1e-12},
                                     'Threshold':{'rtol':1e-12,'atol':0.0}}, metrics={})
        try:
            reference = self.registry.trusted_npz(path, ('t_seconds',) + NUMERIC_KEYS + ALARM_KEYS)
        except AdmissionError as exc:
            comparison['status'] = 'UNAVAILABLE' if exc.code in ('FILE_MISSING','PATH_REJECTED') else 'REJECTED'
            comparison['reason'] = str(exc)
            return comparison
        comparison['reference_sha256'] = self.registry.baseline[path]['sha256']
        visible = reference['t_seconds'] <= result['as_of']
        times = reference['t_seconds'][visible]
        time_equal = np.array_equal(times, result['arrays']['observation_time'])
        comparison['observation_time_equal'] = time_equal
        matched = time_equal
        for key in NUMERIC_KEYS + ALARM_KEYS:
            actual, expected = result['arrays'][key], reference[key][visible]
            atol = 0.0 if key.startswith('threshold') else 1e-12
            compatible = actual.shape == expected.shape
            equal = compatible and (np.array_equal(actual, expected) if key in ALARM_KEYS else
                    np.isfinite(expected).all() and np.allclose(actual, expected, rtol=1e-12, atol=atol))
            metric = {'matched':bool(equal), 'shape':list(actual.shape), 'reference_shape':list(expected.shape)}
            if compatible and key in NUMERIC_KEYS:
                error = np.abs(actual - expected)
                relative = np.divide(error, np.abs(expected), out=np.zeros_like(error), where=expected != 0)
                metric.update(max_absolute_error=float(error.max(initial=0)),
                              max_relative_error_nonzero_reference=float(relative.max(initial=0)),
                              zero_reference_nonzero_actual=int(np.count_nonzero((expected == 0) & (actual != 0))))
            if not equal and compatible:
                bad = actual != expected if key in ALARM_KEYS else ~np.isclose(actual, expected, rtol=1e-12, atol=atol)
                indices = np.argwhere(bad)
                metric['mismatches'] = [{'index':idx.tolist(), 'observation_time':int(times[idx[0]]) if time_equal else None,
                                          'actual':actual[tuple(idx)].item(), 'reference':expected[tuple(idx)].item()}
                                         for idx in indices]
            comparison['metrics'][key] = metric
            matched = matched and equal
        comparison['status'] = 'MATCHED' if matched else 'MISMATCH'
        comparison['reason'] = 'ORIGINAL_TOLERANCES_NO_REFIT_NO_FALLBACK'
        return comparison
