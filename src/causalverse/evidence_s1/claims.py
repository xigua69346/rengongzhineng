"""Closed, reference-only claims. No generated prose or caller-supplied numbers."""
import hashlib
import json
import math

VERSION='s1.1-claims-1'
RELATIONS=('VALIDATED_PATH','STATISTICAL_ASSOCIATION','CANDIDATE_RELATION','HYPOTHESIS')

def catalog(context, snapshot_hash):
    facts={}
    for e in context['evidence']:
        def add(path,value,semantic,dimensions=None,unit=None):
            fid=hashlib.sha256((context['context_id']+e['evidence_id']+e['payload_sha256']+path).encode()).hexdigest()
            facts[fid]=dict(fact_id=fid,evidence_id=e['evidence_id'],payload_sha256=e['payload_sha256'],
                pointer=path,value=value,semantic=semantic,dimensions=dimensions or {},unit=unit,
                source_kind='HISTORICAL_ARCHIVE' if '/original_audit/' in path else 'RECOMPUTED_FROZEN',
                evidence_status=e['status'],method=e['kind'])
        add('/status',e['status'],'COMPUTATION_STATUS')
        if e['status']!='INFERRED':
            add('/data/reason',e['data'].get('reason','OBSERVATION_INCOMPLETE'),'REFUSAL_REASON')
            continue
        d=e['data']
        if e['kind']=='detection':
            for metric in ('T2','SPE','threshold_score','pred_PCA','pred_Threshold'):
                for i,value in enumerate(d['arrays'].get(metric,[])):
                    add(f'/data/arrays/{metric}/{i}',value,'DETECTION_METRIC',dict(metric=metric,observation_time=d['arrays']['observation_time'][i]),'dimensionless')
        elif e['kind'].startswith('diagnosis.'):
            for i,row in enumerate(d['records']):
                for field in ('scores','ranking','raw_candidates','candidates','refused','reason'):
                    add(f'/data/records/{i}/{field}',row[field],'SCORE_NOT_PROBABILITY' if field=='scores' else 'CANDIDATE_NOT_ROOT_CAUSE',dict(field=field,window=context['window']))
        elif e['kind'].startswith('prediction.'):
            for i,row in enumerate(d['records']):
                dims=dict(delta=row['delta'],origin=d['origin'])
                for field in ('computation_status','contract_valid','support_status','uncertainty_status','optimization_allowed','support_reasons','uncertainty_reasons','candidate_audit_status'):
                    add(f'/data/records/{i}/{field}',row[field],'BACKEND_GATE',dict(dims,field=field))
                for name in ('mean','joint_lower','joint_upper'):
                    for h,horizon in enumerate(d['horizons']):
                        for j,target in enumerate(d['targets']):
                            add(f'/data/arrays/{name}/{i}/{h}/{j}',d['arrays'][name][i][h][j],
                                'CONDITIONAL_PREDICTION_NOT_OBSERVATION',dict(dims,horizon=horizon,target=target,metric=name),('°C','°C','kPa')[j])
                for field in ('supported','reasons','normalized_range','status'):
                    audit=next((a for a in d.get('original_audit',[]) if a['delta']==row['delta']),None)
                    if audit is not None:add(f'/data/original_audit/{i}/{field}',audit[field],'AUDIT_ONLY',dict(dims,field=field))
    return dict(schema_version=VERSION,context_id=context['context_id'],snapshot_sha256=snapshot_hash,
                as_of=context['as_of'],chain=context['chain'],facts=list(facts.values()),
                optimization_allowed=False,relation_levels=list(RELATIONS))

def resolve(request, context, snapshot_hash):
    if type(request) is not dict or set(request)!={'schema_version','context_id','snapshot_sha256','claims'}:
        raise ValueError('CLAIM_ENVELOPE')
    if (request['schema_version'],request['context_id'],request['snapshot_sha256'])!=(VERSION,context['context_id'],snapshot_hash):
        raise ValueError('CLAIM_CONTEXT_OR_HASH')
    claims=request['claims']
    if type(claims) is not list or not 1<=len(claims)<=16:raise ValueError('CLAIM_LIMIT')
    facts={f['fact_id']:f for f in catalog(context,snapshot_hash)['facts']};out=[];ids=set()
    for c in claims:
        if type(c) is not dict or set(c)-{'claim_id','claim_type','evidence_refs','comparison_basis','relation_level'} or not {'claim_id','claim_type','evidence_refs'}<=set(c):raise ValueError('CLAIM_FIELDS')
        if type(c['claim_id']) is not str or not 1<=len(c['claim_id'])<=64 or c['claim_id'] in ids:raise ValueError('CLAIM_ID')
        ids.add(c['claim_id']);kind=c['claim_type'];refs=c['evidence_refs']
        if kind not in ('FACT','COMPARISON','RELATION','INSUFFICIENT_EVIDENCE'):raise ValueError('CLAIM_TYPE')
        if type(refs) is not list or not 1<=len(refs)<=8 or any(type(r) is not dict or set(r)!={'evidence_id','fact_id','payload_sha256'} for r in refs):raise ValueError('CLAIM_REFS')
        selected=[]
        for r in refs:
            if type(r['fact_id']) is not str or r['fact_id'] not in facts:raise ValueError('FACT_UNKNOWN')
            f=facts[r['fact_id']]
            if r['evidence_id']!=f['evidence_id'] or r['payload_sha256']!=f['payload_sha256']:raise ValueError('EVIDENCE_HASH_OR_ID')
            selected.append(f)
        row=dict(claim_id=c['claim_id'],claim_type=kind,facts=selected,optimization_allowed=False,
                 validation_status='VERIFIED',source_mode=context['source_mode'])
        if kind=='RELATION':
            if c.get('relation_level') not in RELATIONS or 'comparison_basis' in c:raise ValueError('RELATION_LEVEL')
            # Current S1 snapshots contain no certified relationship facts. Never invent edges.
            row.update(validation_status='INSUFFICIENT_EVIDENCE',refusal_reason='NO_REGISTERED_RELATION_EVIDENCE',relation_level=c['relation_level'])
        else:
            if 'relation_level' in c:raise ValueError('RELATION_FIELD_UNEXPECTED')
            if any(f['evidence_status']!='INFERRED' for f in selected) and kind!='INSUFFICIENT_EVIDENCE':raise ValueError('EVIDENCE_NOT_READY')
            if kind=='INSUFFICIENT_EVIDENCE':row.update(validation_status='INSUFFICIENT_EVIDENCE',refusal_reason='CLAIM_LIMITED_TO_REFERENCED_EVIDENCE')
            if kind=='COMPARISON':
                if c.get('comparison_basis')!='DIFFERENCE' or len(selected)!=2:raise ValueError('COMPARISON_BASIS')
                a,b=selected
                if any(type(f['value']) not in (int,float) or not math.isfinite(f['value']) for f in selected):raise ValueError('COMPARISON_NUMERIC')
                if a['semantic']!=b['semantic'] or a['unit']!=b['unit'] or a['dimensions']!=b['dimensions']:raise ValueError('COMPARISON_NOT_COMPARABLE')
                row.update(comparison_basis='DIFFERENCE',difference=a['value']-b['value'],unit=a['unit'])
            elif 'comparison_basis' in c:raise ValueError('COMPARISON_FIELD_UNEXPECTED')
        out.append(row)
    return dict(schema_version=VERSION,context_id=context['context_id'],snapshot_sha256=snapshot_hash,
                as_of=context['as_of'],claims=out,optimization_allowed=False,llm_enabled=False)
