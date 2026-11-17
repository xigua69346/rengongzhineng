import json,os,time,threading,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
import pytest
from causalverse.autonomy.episode import Episode
from causalverse.autonomy.journal import read_verified
from causalverse.autonomy.gateway import make_server

OUT=Path(os.environ['S3_ACCEPTANCE'])
def wait(predicate,timeout=60):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        if predicate():return
        time.sleep(.05)
    raise AssertionError('DEADLINE')

def test_live_process_pause_resume_fault_and_events():
    e=Episode(OUT/'live','test_owner',rate=500,limit=4500)
    try:
        wait(lambda:e.last_observation is not None)
        e.control('pause');wait(lambda:e.status=='PAUSED');seq=e.last_observation['seq'];time.sleep(.2)
        assert e.last_observation['seq']==seq
        e.inject_fault(14);e.control('resume');wait(lambda:e.status=='COMPLETED',90)
        e.process.join(5);rows=read_verified(e.folder/'events.jsonl')
        obs=[r['payload'] for r in rows if r['kind']=='observation']
        assert len(obs)==4500 and obs[-1]['seq']==4499
        events=[r for r in rows if r['kind']=='anomaly_event' and r['payload']['status'] in ('CANDIDATE','CONFIRMED')]
        assert events,'REAL_DETECTOR_NEVER_TRIGGERED'
        assert len([r for r in rows if r['kind']=='inference'])==15
        assert not any(k in json.dumps(obs) for k in ('rng_state','fault_schedule','valve_position','"idv"'))
        (OUT/'live_summary.json').write_text(json.dumps(dict(episode=e.identity,observations=len(obs),automatic_events=len(events),status=e.status,journal=str(e.folder/'events.jsonl')),indent=2))
    finally:
        e.control('stop');e.process.join(5)
        if e.process.is_alive():e.process.terminate();e.process.join()

def test_one_to_one_and_stop():
    e=Episode(OUT/'realtime','test_owner',rate=1,limit=100)
    try:
        wait(lambda:e.last_observation is not None)
        begin=time.monotonic();n=e.last_observation['seq'];time.sleep(2.2)
        assert 1<=e.last_observation['seq']-n<=3
        e.control('stop');wait(lambda:e.status=='STOPPED');e.process.join(5)
    finally:
        if e.process.is_alive():e.process.terminate();e.process.join()

def test_dead_worker_detected_and_journal_resume():
    e=Episode(OUT/'disconnection','owner',rate=500,limit=14400)
    try:
        wait(lambda:e.last_observation is not None)
        wait(lambda:e.last_observation['seq']>100)
        first=e.view(-1);cursor=first['records'][-1]['seq']
        wait(lambda:e.last_observation['seq']>200)
        resumed=e.view(cursor)
        assert all(r['seq']>cursor for r in resumed['records'])
        assert resumed['records'][0]['seq']==cursor+1
        e.process.terminate();e.process.join(5);wait(lambda:e.status=='UNAVAILABLE_PROCESS_EXIT')
        e.thread.join(3);assert read_verified(e.folder/'events.jsonl')
    finally:
        if e.process.is_alive():e.process.terminate();e.process.join()

def test_http_identity_and_origin(tmp_path):
    server=make_server(tmp_path/'http',0);port=server.server_port
    # Handler requires the configured port; select a real ephemeral port then rebuild.
    server.server_close();server=make_server(tmp_path/'http',port)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    root=f'http://127.0.0.1:{port}'
    try:
        with urllib.request.urlopen(root+'/api/session') as r:session=json.load(r);cookie=r.headers['Set-Cookie'].split(';')[0]
        req=urllib.request.Request(root+'/api/start',data=b'{"rate":1,"limit":3}',headers={'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':session['csrf'],'Origin':'http://evil.example'})
        with pytest.raises(urllib.error.HTTPError) as ex:urllib.request.urlopen(req)
        assert ex.value.code==403
        with pytest.raises(urllib.error.HTTPError) as ex:urllib.request.urlopen(root+'/api/status?episode=other')
        assert ex.value.code==403
        req=urllib.request.Request(root+'/api/start',data=b'{"rate":0,"limit":3}',headers={'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':session['csrf'],'Origin':root})
        with pytest.raises(urllib.error.HTTPError) as ex:urllib.request.urlopen(req)
        assert ex.value.code==400
        headers={'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':session['csrf'],'Origin':root}
        with urllib.request.urlopen(urllib.request.Request(root+'/api/start',data=b'{"rate":500,"limit":3}',headers=headers)) as r:identity=json.load(r)
        with urllib.request.urlopen(root+'/api/session') as r:other_cookie=r.headers['Set-Cookie'].split(';')[0]
        denied=urllib.request.Request(root+'/api/status?episode='+identity['episode_id'],headers={'Cookie':other_cookie})
        with pytest.raises(urllib.error.HTTPError) as ex:urllib.request.urlopen(denied)
        assert ex.value.code==403
    finally:server.shutdown();server.server_close();t.join()
