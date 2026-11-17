"""Loopback monitoring workbench. No LLM, control override or optimization routes."""
import argparse,json,secrets,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from .episode import Episode
from .contracts import SCHEMA
from .protection import ROOT,verify

def make_server(root,port=8770):
    sessions={};episodes={};lock=threading.Lock();assets=Path(__file__).parent/'console'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,code,data,mime='application/json',cookie=None):
            payload=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(code);self.send_header('Content-Type',mime+'; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers();self.wfile.write(payload)
        def admit(self,post=False):
            hosts=(f'127.0.0.1:{port}',f'localhost:{port}')
            if self.headers.get('Host') not in hosts:raise PermissionError('HOST')
            if post and self.headers.get('Origin') not in tuple('http://'+h for h in hosts):raise PermissionError('ORIGIN')
            cookie=SimpleCookie(self.headers.get('Cookie',''));sid=cookie['s3'].value if 's3' in cookie else None
            if sid not in sessions:raise PermissionError('SESSION')
            if post and self.headers.get('X-CSRF-Token')!=sessions[sid]:raise PermissionError('CSRF')
            return sid
        def do_GET(self):
            try:
                path=urlsplit(self.path).path
                if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):raise PermissionError('HOST')
                if path=='/api/session':
                    if len(sessions)>=32:return self.reply(429,{'error':'SESSION_LIMIT'})
                    cookie=SimpleCookie(self.headers.get('Cookie',''));sid=cookie['s3'].value if 's3' in cookie else None
                    if sid not in sessions:sid=secrets.token_hex(24);sessions[sid]=secrets.token_hex(24)
                    return self.reply(200,dict(csrf=sessions[sid],schema=SCHEMA),cookie=f's3={sid}; HttpOnly; SameSite=Strict; Path=/')
                if path in ('/','/app.js','/style.css'):
                    name='index.html' if path=='/' else path[1:]
                    return self.reply(200,(assets/name).read_bytes(),{'index.html':'text/html','app.js':'text/javascript','style.css':'text/css'}[name])
                sid=self.admit();query=parse_qs(urlsplit(self.path).query)
                if path=='/api/status':
                    eid=query.get('episode',[''])[0];e=episodes.get(eid)
                    if e is None or e.owner!=sid:raise PermissionError('EPISODE')
                    return self.reply(200,e.view(int(query.get('after',['-1'])[0])))
                return self.reply(404,dict(error='NOT_FOUND'))
            except PermissionError:return self.reply(403,dict(error='ACCESS_DENIED'))
            except (ValueError,TypeError):return self.reply(400,dict(error='INVALID_REQUEST'))
        def do_POST(self):
            try:
                sid=self.admit(True)
                if self.headers.get('Content-Type')!='application/json' or self.headers.get('Transfer-Encoding'):raise ValueError('JSON')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=1024:raise ValueError('BODY_LIMIT')
                def pairs(items):
                    result={}
                    for key,value in items:
                        if key in result:raise ValueError('DUPLICATE_KEY')
                        result[key]=value
                    return result
                def bad_constant(value):raise ValueError('NONFINITE_JSON')
                data=json.loads(self.rfile.read(n),object_pairs_hook=pairs,parse_constant=bad_constant)
                if type(data) is not dict:raise ValueError('OBJECT')
                with lock:
                    if self.path=='/api/start':
                        if set(data)!={'rate','limit'}:raise ValueError('FIELDS')
                        if any(e.process.is_alive() for e in episodes.values()):return self.reply(409,dict(error='PRODUCTION_ALREADY_RUNNING'))
                        e=Episode(root,sid,**data);episodes[e.identity['episode_id']]=e
                        return self.reply(201,e.identity)
                    if self.path=='/api/control':
                        if set(data)!={'episode_id','op'}:raise ValueError('FIELDS')
                        e=episodes.get(data['episode_id'])
                        if e is None or e.owner!=sid:raise PermissionError('EPISODE')
                        e.control(data['op']);return self.reply(200,dict(status='REQUESTED',op=data['op']))
                    if self.path=='/api/operator-fault':
                        if set(data)!={'episode_id','fault_id'}:raise ValueError('FIELDS')
                        e=episodes.get(data['episode_id'])
                        if e is None or e.owner!=sid:raise PermissionError('EPISODE')
                        e.inject_fault(data['fault_id']);return self.reply(200,dict(status='OPERATOR_REQUESTED_NOT_AI_DECISION'))
                return self.reply(404,dict(error='NOT_FOUND'))
            except PermissionError:return self.reply(403,dict(error='ACCESS_DENIED'))
            except (ValueError,TypeError,KeyError):return self.reply(400,dict(error='INVALID_REQUEST'))
        def do_DELETE(self):self.reply(405,dict(error='NOT_ALLOWED'))
        do_PUT=do_DELETE;do_PATCH=do_DELETE
    class Server(ThreadingHTTPServer):
        allow_reuse_address=False
    server=Server(('127.0.0.1',port),Handler);server.episodes=episodes
    return server

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8770);args=parser.parse_args()
    batch=ROOT/'artifacts/autonomy'/('s3_'+secrets.token_hex(12))
    server=make_server(batch/'runs',args.port) # exclusive bind is the port occupancy check
    try:
        before=verify()
        if any(before[k] for k in ('changed_hashes','missing_files','unreadable_files','verification_errors')):raise RuntimeError('PROTECTION_FAILED')
        batch.mkdir(parents=True,exist_ok=True)
        with (batch/'protection_start.json').open('x',encoding='utf-8') as f:json.dump(before,f,indent=2)
        print('S3 http://127.0.0.1:'+str(args.port)+' batch='+str(batch),flush=True)
        server.serve_forever()
    finally:
        for e in server.episodes.values():e.control('stop')
        for e in server.episodes.values():
            e.process.join(5)
            if e.process.is_alive():e.process.terminate();e.process.join(2)
        server.server_close()
if __name__=='__main__':main()
