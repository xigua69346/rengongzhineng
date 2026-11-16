"""Real frozen inference, strict public projections and hash-verified snapshots."""
import hashlib
import json
import secrets
import threading
from pathlib import Path
from causalverse.ai_runtime.registry import Registry
from causalverse.ai_runtime.identity import IdentityStore
from causalverse.ai_runtime.detection_runtime import DetectionRuntime
from causalverse.ai_runtime.diagnosis_runtime import DiagnosisRuntime
from causalverse.ai_runtime.prediction_runtime import PredictionRuntime

VERSION = 's1-evidence-1'

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def pick(obj, keys):
    return {k: obj[k] for k in keys if k in obj}

class EvidenceService:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.registry = Registry()
        self.identities = IdentityStore(self.registry)
        self.cases = {}
        refs = [('D3', n) for n, r in self.identities.d3.items() if r['split'] == 'test']
        refs += [('D511', n) for n, r in self.identities.d511.items() if r['split'] == 'test' and r['delta'] == 0]
        assert len(refs) == 160
        secrets.SystemRandom().shuffle(refs)
        for chain, name in refs:
            key = secrets.token_hex(16)
            self.cases[key] = dict(selection_id=key, alias='案例-' + secrets.token_hex(4), chain=chain,
                                   data_ref=chain + ':' + name)
        write_new(self.root / '_private/cases.json', self.cases)
        self.detection = DetectionRuntime(self.root / '_private/inference/detection', self.registry)
        self.diagnosis = DiagnosisRuntime(self.root / '_private/inference/diagnosis', self.registry)
        self.prediction = PredictionRuntime(self.root / '_private/inference/prediction', self.registry)
        self.index = {}
        self.lock = threading.Lock()

    def catalog(self):
        return [pick(c, ('selection_id', 'alias', 'chain')) for c in self.cases.values()]

    def fact_catalog(self, cid, owner):
        from .claims import catalog
        context=self.get(cid,owner)
        return catalog(context,self.index[cid]['snapshot_sha256'])

    def resolve_claims(self, request, owner):
        from .claims import resolve
        if type(request) is not dict or type(request.get('context_id')) is not str:
            raise ValueError('CLAIM_CONTEXT_REQUIRED')
        context=self.get(request['context_id'],owner)
        return resolve(request,context,self.index[context['context_id']]['snapshot_sha256'])

    def create(self, request, owner):
        if set(request) != {'selection_id', 'as_of', 'window'}:
            raise ValueError('REQUEST_FIELDS')
        case = self.cases.get(request['selection_id'])
        if case is None:
            raise ValueError('UNKNOWN_SELECTION')
        t, window = request['as_of'], request['window']
        if type(t) is not int or not 0 <= t <= (14399 if case['chain'] == 'D3' else 6120):
            raise ValueError('AS_OF_INVALID')
        if type(window) is not int or window not in (180, 600, 1800):
            raise ValueError('WINDOW_INVALID')
        with self.lock:
            if len(self.index) >= 128:
                raise ValueError('CONTEXT_LIMIT')
            return self._compute(case, t, window, owner)

    def _compute(self, case, t, window, owner):
        cid = secrets.token_hex(16)
        context = dict(schema_version=VERSION, context_id=cid, alias=case['alias'], chain=case['chain'],
                       as_of=t, window=window, source_mode='HISTORICAL_TEP_SIMULATION',
                       llm_enabled=False, optimization_allowed=False, evidence=[])
        context['knowledge_sha256'] = digest(Path(__file__).parent / 'knowledge.json')
        context['prompt_version'] = 's1-evidence-policy-1'
        identity, _, folder, trajectory = self.identities.resolve(case['data_ref'])
        private = dict(data_ref=case['data_ref'], owner=owner, identity=vars(identity),
                       manifest=folder + '/manifest.json', trajectory=trajectory, sources=[])
        def add(kind, result, payload=None):
            eid = secrets.token_hex(16)
            status = result.get('status', 'UNAVAILABLE')
            # A failed protected read is never converted into a positive evidence item.
            if status in ('FAILED', 'REJECTED'):
                write_new(self.root / '_private/failures' / (eid + '.json'),
                          dict(data_ref=case['data_ref'], result=pick(result, ('status', 'reason'))))
            public = dict(evidence_id=eid, context_id=cid, kind=kind, status=status,
                          execution_mode=result.get('execution_mode', 'recomputed_frozen'),
                          model=pick(result, ('model_id', 'model_hash', 'model_version')),
                          elapsed_ms=result.get('elapsed_ms'), data=payload or {})
            public['payload_sha256'] = hashlib.sha256(json.dumps(public, sort_keys=True,
                ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            private['sources'].append(dict(evidence_id=eid, **pick(result, (
                'inference_id', 'source_hash', 'observation_payload_hash', 'inference_identity_hash',
                'context_id', 'source_file_hash', 'arrays_file_sha256', 'reason'))))
            context['evidence'].append(public)
        ref = case['data_ref']
        if case['chain'] == 'D3':
            r = self.detection.detect(ref, as_of=t, request_id=cid + '-detect')
            arrays = r.get('arrays', {})
            fields = ('observation_time', 'T2', 'SPE', 'threshold_score', 'projection',
                      'T2_contribution', 'SPE_contribution', 'threshold_contribution',
                      'pred_T2', 'pred_SPE', 'pred_PCA', 'pred_Threshold')
            add('detection', r, dict(arrays={k: arrays[k].tolist() for k in fields if k in arrays},
                                     limits=r.get('limits', {}), observation_role='PAST_OBSERVATION'))
        else:
            add('detection', dict(status='UNAVAILABLE', execution_mode='NOT_APPLICABLE'),
                dict(reason='D3_41_XMEAS_DETECTOR_NOT_REGISTERED_FOR_D511'))
        for method in ('static', 'VAR', 'logistic'):
            r = self.diagnosis.diagnose([ref], kind=method, window=window, as_of=t, request_id=cid + method)
            rows = [pick(row, ('scores', 'ranking', 'raw_candidates', 'candidates', 'refused', 'reason', 'status',
                               'observation_time', 'columns')) for row in r.get('records', [])]
            add('diagnosis.' + method, r, dict(records=rows, score_semantics='NOT_PROBABILITY',
                                              conclusion_boundary='MODEL_CANDIDATE_NOT_PHYSICAL_ROOT_CAUSE'))
        if case['chain'] == 'D511':
            for method in ('action', 'delta'):
                r = self.prediction.predict(ref, kind=method, as_of=t, request_id=cid + method)
                data = dict(records=r.get('records', []), targets=['T9', 'C21', 'P7'],
                            horizons=[10, 30, 60, 120, 300, 600], origin=5400,
                            observation_time=list(r.get('observation_time', [])),
                            observation_role='PAST_OBSERVATION', output_role='CONDITIONAL_PREDICTION_NOT_FUTURE_TRUTH')
                data['arrays'] = {k: a.tolist() for k, a in r.get('arrays', {}).items()}
                if r['status'] == 'INFERRED':
                    comparison = self.prediction.compare_archive(r)
                    data['historical_comparison'] = pick(comparison, ('status', 'rtol', 'atol'))
                    # The original gates are read independently, after inference, using private identity only.
                    _, record, _, _ = self.identities.resolve(ref)
                    rows = self.registry.trusted_json('artifacts/d5_1_1/candidate_disagreement.json')['rows']
                    support = self.registry.trusted_json('artifacts/d5_1_1/support_results.json')
                    audit = []
                    for j, row in enumerate(rows):
                        # Frozen archive has explicit private identifiers; never publish them.
                        if (row['seed'], row['mechanism']) == (record['seed'], record['mechanism']):
                            original = row['models'][method]
                            audit.append(dict(delta=row['delta'], status='AUDIT_ONLY',
                                supported=original['supported'], reasons=original['reasons'],
                                normalized_range=original['normalized_range'],
                                base_support=support[j]['checks']['by_model'][method]))
                    data['original_audit'] = audit
                    data['original_audit_matches_recomputation'] = comparison['status'] == 'MATCHED'
                add('prediction.' + method, r, data)
        else:
            add('prediction', dict(status='UNAVAILABLE', execution_mode='NOT_APPLICABLE'),
                dict(reason='NO_REGISTERED_D3_TO_D511_PAIRING'))
        path = self.root / 'snapshots' / (cid + '.json')
        write_new(path, context)
        private.update(snapshot_sha256=digest(path), context_id=cid)
        write_new(self.root / '_private/mappings' / (cid + '.json'), private)
        self.index[cid] = private
        return self.get(cid, owner)

    def get(self, cid, owner):
        record = self.index.get(cid)
        if record is None or record['owner'] != owner:
            raise PermissionError('CONTEXT_DENIED')
        path = self.root / 'snapshots' / (cid + '.json')
        if digest(path) != record['snapshot_sha256']:
            raise ValueError('SNAPSHOT_HASH_MISMATCH')
        return json.loads(path.read_text(encoding='utf-8'))

    def evidence(self, eid, owner):
        for cid, item in list(self.index.items()):
            if item['owner'] == owner:
                for e in self.get(cid, owner)['evidence']:
                    if e['evidence_id'] == eid:
                        return e
        raise PermissionError('EVIDENCE_DENIED')

    def validate_claim(self, claim, owner):
        if set(claim) != {'context_id', 'evidence_id', 'claim_type'}:
            raise ValueError('CLAIM_FIELDS')
        context = self.get(claim['context_id'], owner)
        e = next((e for e in context['evidence'] if e['evidence_id'] == claim['evidence_id']), None)
        if e is None:
            raise ValueError('CLAIM_EVIDENCE_MISMATCH')
        allowed = {'INSUFFICIENT_EVIDENCE'} if e['status'] != 'INFERRED' else {'COMPUTATION_AVAILABLE'}
        if claim['claim_type'] not in allowed:
            raise ValueError('UNSUPPORTED_CLAIM')
        return True
