"""Failure diagnostics must not disclose credentials or relax the explanation validator."""
import json,os
from pathlib import Path
import pytest
from causalverse.evidence_s1.service import EvidenceService
from causalverse.evidence_s2.runtime import ExplanationRuntime

def test_failed_output_is_private_redacted_and_still_rejected(monkeypatch):
    root=Path(os.environ['S1_ACCEPTANCE'])
    s=EvidenceService(root/'diagnostic_ml');c=next(c for c in s.catalog() if c['chain']=='D3')
    ctx=s.create(dict(selection_id=c['selection_id'],as_of=5400,window=1800),'owner')
    monkeypatch.setenv('DEEPSEEK_API_KEY','SYNTHETIC_DIAGNOSTIC_SECRET')
    class Fixture:
        is_test_fixture=True;model='SYNTHETIC_TEST_FIXTURE';base='NO_NETWORK'
        def configured(self):return True
        def complete(self,msg):
            return dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(unexpected='SYNTHETIC_DIAGNOSTIC_SECRET'))))]),1
    e=ExplanationRuntime(s,root/'diagnostic_ai',Fixture())
    result=e.run(ctx['context_id'],'owner')
    assert result['status']=='REJECTED' and result['analysis']==[]
    assert result['validation_error_code']=='AI_ENVELOPE'
    files=list((root/'diagnostic_ai').glob('*_untrusted_output.json'));assert len(files)==1
    text=files[0].read_text(encoding='utf8')
    assert 'SYNTHETIC_DIAGNOSTIC_SECRET' not in text and '[REDACTED]' in text
    assert 'unexpected' not in json.dumps(result)
