import hashlib,json,re,secrets,threading,time,os
from datetime import datetime,timezone
from pathlib import Path
from causalverse.evidence_s1.service import write_new
from .client import DeepSeekClient,APIError,parse
from .explanation import prepare,messages,validate,VERSION,PROMPT_VERSION

class ExplanationRuntime:
    def __init__(self,service,root,client=None):
        self.service=service;self.root=Path(root);self.client=client or DeepSeekClient()
        self.lock=threading.Lock();self.last=0;self.calls=0;self.cache={}

    def config(self):return dict(model=self.client.model,api_configured=self.client.configured(),endpoint=self.client.base,contract=VERSION,optimization_allowed=False)

    def run(self,cid,owner):
        bundle=prepare(self.service,cid,owner)
        if not self.lock.acquire(False):raise ValueError('AI_BUSY')
        try:
            identity=(owner,cid)
            if identity in self.cache:return self.cache[identity]
            start=time.perf_counter();request_id=secrets.token_hex(16)
            record=dict(request_id=request_id,context_id=cid,model=self.client.model,contract=VERSION,
                        requested_at_utc=datetime.now(timezone.utc).isoformat(),
                        snapshot_sha256=bundle['snapshot_sha256'],status='NOT_CONFIGURED',api_call_made=False,
                        usage=None,cost_cny=None,cost_status='NO_CALL',analysis=[],optimization_allowed=False,
                        generated_content_origin='NONE',ml_evidence_preserved=True)
            fixture=bool(getattr(self.client,'is_test_fixture',False))
            record['transport_mode']='TEST_FIXTURE_ONLY' if fixture else 'OFFICIAL_API'
            if self.client.configured():
                if self.calls>=10 or time.monotonic()-self.last<30:raise ValueError('AI_RATE_LIMIT')
                self.calls+=1;self.last=time.monotonic()
                write_new(self.root/(request_id+'_input.json'),bundle)
                record['input_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                record.update(api_call_made=not fixture,transport_invoked=True,cost_status='PROVIDER_USAGE_REQUIRED')
                try:
                    payload=messages(bundle)
                    record['prompt_version']=PROMPT_VERSION
                    record['prompt_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    data,attempts=self.client.complete(payload)
                    record['attempts']=attempts
                    usage=data.get('usage')
                    if isinstance(usage,dict):record['usage']={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens') and type(v) is int and 0<=v<=2000000}
                    # No fabricated invoice: peak/off-peak/cache tariff requires accounting time and actual usage.
                    record['cost_status']='USAGE_RECORDED_INVOICE_NOT_VERIFIED' if record['usage'] else 'USAGE_UNAVAILABLE'
                    provider_id=data.get('id','')
                    if isinstance(provider_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,120}',provider_id):record['provider_request_id']=provider_id
                    response=parse(data)
                    # Private failure evidence only; never send unvalidated output to the console.
                    # Redact the backend secret before serialization to disk, including accidental echoes.
                    serialized=json.dumps(response,ensure_ascii=False,allow_nan=False)
                    secret=os.environ.get('DEEPSEEK_API_KEY','').strip()
                    if secret:serialized=serialized.replace(secret,'[REDACTED]')
                    write_new(self.root/(request_id+'_untrusted_output.json'),
                              dict(trust_status='UNVALIDATED_NOT_FOR_DISPLAY',output=json.loads(serialized)))
                    analysis=validate(self.service,owner,bundle,response)
                    # Save only strictly validated reference-only model output, never arbitrary upstream text.
                    write_new(self.root/(request_id+'_validated_model_output.json'),response)
                    record.update(status='VALIDATED',analysis=analysis,generated_content_origin='TEST_FIXTURE_STRUCTURED_SELECTION' if fixture else 'REAL_DEEPSEEK_STRUCTURED_SELECTION',
                                  text_origin='BACKEND_VERIFIED_RENDERING')
                except APIError as exc:record.update(status='UNAVAILABLE',error_code=exc.code,http_status=exc.http_status)
                except (ValueError,KeyError,TypeError,IndexError) as exc:
                    code=str(exc)
                    safe=code if re.fullmatch(r'[A-Z_]{1,80}',code) else 'UNCLASSIFIED_VALIDATION_FAILURE'
                    record.update(status='REJECTED',error_code='AI_EVIDENCE_VALIDATION_FAILED',validation_error_code=safe)
                except Exception:record.update(status='UNAVAILABLE',error_code='AI_ADAPTER_FAILURE')
            record['elapsed_ms']=(time.perf_counter()-start)*1000
            write_new(self.root/(request_id+'_audit.json'),record)
            if record['status']=='VALIDATED':self.cache[identity]=record
            return record
        finally:self.lock.release()
