"""Official DeepSeek JSON completion via stdlib. No SDK, key logging or redirects."""
import json,os,socket,time,urllib.request,urllib.error
from urllib.parse import urlsplit

class APIError(Exception):
    def __init__(self,code,http_status=None):self.code=code;self.http_status=http_status;super().__init__(code)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise APIError('REDIRECT_REJECTED')

class DeepSeekClient:
    def __init__(self):
        self.model=os.environ.get('DEEPSEEK_MODEL','deepseek-flash')
        self.base=os.environ.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')
        self.timeout=30
        if not self.model or len(self.model)>80 or any(ord(c)<32 for c in self.model):raise APIError('MODEL_CONFIG')
        parsed=urlsplit(self.base)
        # Configurable official HTTPS endpoint only: no key forwarding to arbitrary hosts.
        if parsed.scheme!='https' or parsed.hostname!='api.deepseek.com' or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None,443) or parsed.path not in ('','/v1'):raise APIError('ENDPOINT_CONFIG')

    def configured(self):return bool(os.environ.get('DEEPSEEK_API_KEY','').strip())

    def complete(self,messages):
        key=os.environ.get('DEEPSEEK_API_KEY','').strip()
        if not key:raise APIError('KEY_MISSING')
        body=json.dumps(dict(model=self.model,messages=messages,response_format={'type':'json_object'},thinking={'type':'disabled'},stream=False,max_tokens=1800),ensure_ascii=False,allow_nan=False).encode()
        if len(body)>60000:raise APIError('CONTEXT_TOO_LARGE')
        req=urllib.request.Request(self.base+'/chat/completions',data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
        opener=urllib.request.build_opener(NoRedirect())
        # At most one retry on explicit rate-limit or unavailable responses. Never retry timeouts/invalid content.
        for attempt in range(2):
            try:
                with opener.open(req,timeout=self.timeout) as r:
                    raw=r.read(196609)
                    if len(raw)>196608:raise APIError('RESPONSE_TOO_LARGE')
                    data=json.loads(raw)
                    return data,attempt+1
            except urllib.error.HTTPError as exc:
                status=exc.code;exc.close()
                if status in (429,503) and attempt==0:time.sleep(.5);continue
                raise APIError('HTTP_ERROR',status) from None
            except (socket.timeout,TimeoutError):raise APIError('TIMEOUT') from None
            except urllib.error.URLError:raise APIError('NETWORK_ERROR') from None
            except (ValueError,KeyError,TypeError):raise APIError('INVALID_API_JSON') from None

def parse(data):
    try:
        choice=data['choices'][0]
        if choice['finish_reason']!='stop':raise APIError('OUTPUT_TRUNCATED_OR_REFUSED')
        content=choice['message']['content']
        if not isinstance(content,str) or not content.strip():raise APIError('EMPTY_OUTPUT')
        def pairs(items):
            d={}
            for k,v in items:
                if k in d:raise ValueError('duplicate')
                d[k]=v
            return d
        return json.loads(content,object_pairs_hook=pairs)
    except APIError:raise
    except (KeyError,IndexError,TypeError,ValueError):raise APIError('INVALID_MODEL_FORMAT') from None
