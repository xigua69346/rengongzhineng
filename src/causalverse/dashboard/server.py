"""Local-only HTTP adapter for immutable experimental artifacts."""
import argparse,json,mimetypes
from pathlib import Path
from functools import lru_cache
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
@lru_cache(maxsize=1)
def runs():return [r for r in read('artifacts/d3/dataset/split_plan.json')['runs'] if r['split']=='test']
def spec(rid):
    for r in runs():
        if r['dataset_run_id']==rid:return r
    raise ValueError('Unknown run_id')
@lru_cache(maxsize=4)
def trajectory(rid):
    r=spec(rid);folder=ROOT/'artifacts/d3/dataset/raw'/rid
    with np.load(folder/'trajectory.npz') as p:
        m=p['XMEAS'];u=p['XMV'];values=np.column_stack([m[:,8],m[:,20],m[:,6],u[:,9]])
    return dict(run=r,time=list(range(len(values))),values=values.tolist(),source=f'artifacts/d3/dataset/raw/{rid}/trajectory.npz',mode='TEP历史仿真回放',sample_seconds=1,manifest=read(str(folder.relative_to(ROOT)/'manifest.json')))
def detection(rid):
    spec(rid)
    with np.load(ROOT/'artifacts/d3/detection'/f'{rid}.npz') as p:
        data={k:p[k].tolist() for k in ('t_seconds','y','T2','SPE','threshold_score','pred_Threshold','pred_T2','pred_SPE','pred_PCA')}
        data['contributions']=p['SPE_contribution'].tolist()
        data['variable_threshold_scores']=p['threshold_contribution'].tolist()
    return dict(**data,limits=read('artifacts/d3/detection/model_manifest.json')['limits'],source=f'artifacts/d3/detection/{rid}.npz',sample_seconds=180)
def diagnosis(rid,kind,window):
    spec(rid)
    if kind not in ('static','VAR','logistic') or window not in (180,600,1800):raise ValueError('Unknown model/window')
    return next(r for r in read('artifacts/d5_1_2/diagnoses.json') if r['run_id']==rid and r['kind']==kind and r['window']==window and r['split']=='test')
def uncertainty(kind,seed,mechanism,dose):
    if kind not in ('action','delta','PI','PI_stable') or seed not in range(631000,631020) or mechanism not in (0,4,11,14) or dose not in (0,1,5):raise ValueError('Unknown saved prediction')
    i=(seed-631000)*12+(0,4,11,14).index(mechanism)*3+(0,1,5).index(dose)
    with np.load(ROOT/f'artifacts/d5_1_1/intervals_{kind}_test.npz') as p:
        assert list(p['identifiers'][i])==[seed,mechanism,dose]
        data={k:p[k][i].tolist() for k in ('prediction','truth','joint_lower','joint_upper')};data['horizons']=p['horizons'].tolist()
    return dict(**data,source=f'artifacts/d5_1_1/intervals_{kind}_test.npz',trusted_for_optimization=False)
def api(path,q):
    get=lambda k,d=None:q.get(k,[d])[0]
    if path=='/api/runs':return runs()
    if path=='/api/trajectory':return trajectory(get('run'))
    if path=='/api/detection':return detection(get('run'))
    if path=='/api/diagnosis':return diagnosis(get('run'),get('kind','VAR'),int(get('window','1800')))
    if path=='/api/uncertainty':return uncertainty(get('kind','delta'),int(get('seed','631000')),int(get('mechanism','14')),int(get('dose','1')))
    if path=='/api/research':return dict(metrics=read('artifacts/d5_1_2/metrics.json'),uncertainty=read('artifacts/d5_1_1/final_summary.json')['models'],graph=read('artifacts/d4/protocol.json'),optimization_allowed=False)
    raise KeyError('Unknown endpoint')

class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,mime):
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_POST(self):self.send(405,b'{"error":"Read-only service"}','application/json')
    do_PUT=do_POST;do_DELETE=do_POST;do_PATCH=do_POST
    def do_GET(self):
        u=urlparse(self.path)
        try:
            if u.path.startswith('/api/'):
                result=api(u.path,parse_qs(u.query));self.send(200,json.dumps(result,ensure_ascii=False,allow_nan=False).encode(),'application/json; charset=utf-8');return
            base=ROOT/'frontend/dist';p=(base/u.path.lstrip('/')).resolve()
            if not p.is_relative_to(base.resolve()):raise ValueError('Invalid path')
            if not p.is_file():p=base/'index.html'
            self.send(200,p.read_bytes(),mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
        except (ValueError,TypeError):self.send(400,b'{"error":"Invalid request"}','application/json')
        except (KeyError,StopIteration):self.send(404,b'{"error":"Not found"}','application/json')
        except Exception:
            self.send(503,b'{"error":"Artifact unavailable; verify local installation"}','application/json')
def main():
    a=argparse.ArgumentParser();a.add_argument('--port',type=int,default=8766);args=a.parse_args()
    print(f'CausalVerse read-only dashboard: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__':main()
