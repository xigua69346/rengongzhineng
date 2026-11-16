"""Prompt alignment adds provider constraints; original validator stays strict."""
import json,hashlib,os
from pathlib import Path
import pytest
from causalverse.evidence_s1.service import EvidenceService
from causalverse.evidence_s2.explanation import prepare,messages,validate

def test_prompt_sends_same_reference_limit_as_contract():
    prompt=messages({})[0]['content']
    assert 'findings为2至8项' in prompt and 'findings为1至8项' not in prompt
    assert '"maxItems": 2' in prompt
    assert 'INSUFFICIENT_ROOT_CAUSE各选且仅选1条引用' in prompt

def test_three_references_still_rejected():
    root=Path(os.environ['S1_ACCEPTANCE'])
    s=EvidenceService(root/'prompt_alignment_ml')
    case=next(c for c in s.catalog() if c['chain']=='D3')
    ctx=s.create(dict(selection_id=case['selection_id'],as_of=5400,window=1800),'owner')
    bundle=prepare(s,ctx['context_id'],'owner');f=bundle['facts'][0]
    ref={k:f[k] for k in ('evidence_id','fact_id','payload_sha256')}
    response={k:bundle[k] for k in ('schema_version','context_id','snapshot_sha256')}
    response['findings']=[dict(rule='METRIC_EVIDENCE',evidence_refs=[ref]),dict(rule='INSUFFICIENT_ROOT_CAUSE',evidence_refs=[ref,ref,ref])]
    with pytest.raises(ValueError,match='AI_REFERENCE_LIMIT'):validate(s,'owner',bundle,response)
