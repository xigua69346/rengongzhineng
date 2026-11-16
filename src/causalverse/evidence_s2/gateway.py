"""S2 adapter around unchanged S1.1 HTTP handlers and session ownership."""
import argparse,json,secrets
from pathlib import Path
from causalverse.evidence_s1.gateway import make_server
from causalverse.evidence_s1.service import EvidenceService
from .runtime import ExplanationRuntime
from .protection import verify

ASSETS=Path(__file__).parent/'console'

def attach(server,engine):
    Base=server.RequestHandlerClass;nonces={}
    class Handler(Base):
        def do_GET(self):
            try:
                sid=self.admit()
                assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css'),'/ai.js':('ai.js','text/javascript')}
                if self.path in assets:
                    name,mime=assets[self.path];return self.reply(200,(ASSETS/name).read_bytes(),mime)
                if self.path=='/api/ai/session':
                    if sid is None:return self.reply(403,dict(error='SESSION_REQUIRED'))
                    if sid not in nonces:nonces[sid]=secrets.token_hex(24)
                    return self.reply(200,dict(engine.config(),csrf=nonces[sid]))
            except PermissionError:return self.reply(403,dict(error='ACCESS_DENIED'))
            return super().do_GET()

        def do_POST(self):
            if self.path!='/api/ai/explain':return super().do_POST()
            try:
                sid=self.admit()
                if sid is None or sid not in nonces or self.headers.get('X-CSRF-Token')!=nonces[sid]:return self.reply(403,dict(error='ACCESS_DENIED'))
                if self.headers.get('Content-Type')!='application/json' or self.headers.get('Transfer-Encoding'):return self.reply(400,dict(error='JSON_REQUIRED'))
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=512:return self.reply(413,dict(error='BODY_LIMIT'))
                def pairs(items):
                    d={}
                    for k,v in items:
                        if k in d:raise ValueError('DUPLICATE')
                        d[k]=v
                    return d
                data=json.loads(self.rfile.read(length),object_pairs_hook=pairs)
                if type(data) is not dict or set(data)!={'context_id'} or type(data['context_id']) is not str:raise ValueError('REQUEST_FIELDS')
                return self.reply(200,engine.run(data['context_id'],sid))
            except PermissionError:return self.reply(403,dict(error='ACCESS_DENIED'))
            except (ValueError,TypeError):return self.reply(400,dict(error='INVALID_OR_LIMITED_AI_REQUEST'))
            except Exception:return self.reply(503,dict(error='AI_UNAVAILABLE_ML_PRESERVED'))
    server.RequestHandlerClass=Handler
    return server

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8769);args=p.parse_args()
    root=Path(__file__).resolve().parents[3];batch=root/'artifacts/ai_s2_runs'/secrets.token_hex(16)
    server=make_server(None,args.port)
    try:
        verify(root,batch/'protection_start.json')
        service=EvidenceService(batch/'evidence');engine=ExplanationRuntime(service,batch/'ai')
        server.server_close();server=attach(make_server(service,args.port),engine)
        print('S2 http://127.0.0.1:'+str(args.port)+' api_configured='+str(engine.client.configured())+' batch='+str(batch),flush=True)
        server.serve_forever()
    finally:server.server_close()
if __name__=='__main__':main()
