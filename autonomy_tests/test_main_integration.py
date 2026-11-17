"""8768 integration acceptance; uses real TEP, no paid APIs or mock measurements."""
import http.cookiejar,json,os,socket,threading,time
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.error import HTTPError
import pytest
from causalverse.dashboard.server import make_main_server

def test_original_main_and_real_monitoring():
    root=Path(os.environ['MAIN_ACCEPTANCE'])/'http_real'
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    server=make_main_server(root,port);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{port}';jar=http.cookiejar.CookieJar();client=build_opener(HTTPCookieProcessor(jar))
    def get(path):
        with client.open(url+path,timeout=20) as response:return json.load(response)
    def post(path,data,token):
        req=Request(url+path,data=json.dumps(data).encode(),headers={'Origin':url,'Content-Type':'application/json','X-CSRF-Token':token})
        with client.open(req,timeout=20) as response:return json.load(response)
    try:
        with client.open(url) as r:assert '/assets/index-' in r.read().decode()
        assert len(get('/api/runs'))==80
        assert get('/api/research')['optimization_allowed'] is False
        session=get('/api/session');assert any(c.name=='cv8768' for c in jar);assert not any(c.name=='s3' for c in jar)
        episode=post('/api/start',dict(rate=500,limit=2600),session['csrf']);eid=episode['episode_id']
        post('/api/operator-fault',dict(episode_id=eid,fault_id=14),session['csrf'])
        end=time.monotonic()+45;state=None
        while time.monotonic()<end:
            state=get('/api/status?episode='+eid)
            if state['status']=='COMPLETED':break
            time.sleep(.1)
        assert state['status']=='COMPLETED'
        assert state['latest']['measurement_time']==2599
        assert any(r['kind']=='inference' for r in state['records'])
        assert any(r['kind']=='anomaly_event' and r['payload']['status'] in ('CANDIDATE','CONFIRMED') for r in state['records'])
        assert state['optimization_allowed'] is False
        other=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        with other.open(url+'/api/session'):pass
        with pytest.raises(HTTPError) as ex:other.open(url+'/api/status?episode='+eid)
        assert ex.value.code==403
        (Path(os.environ['MAIN_ACCEPTANCE'])/'real_main_result.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    finally:
        for episode in server.episodes.values():
            episode.control('stop');episode.process.join(5)
            if episode.process.is_alive():episode.process.terminate();episode.process.join()
        server.shutdown();server.server_close();thread.join()

@pytest.mark.parametrize('tampered',[False,True])
def test_startup_release_pin(monkeypatch,tampered):
    import causalverse.dashboard.server as main
    import causalverse.autonomy.protection as protection
    class StopAfterAdmission:
        episodes={}
        def serve_forever(self):raise RuntimeError('ADMISSION_PASSED_TEST_ONLY')
        def server_close(self):pass
    changed=['frontend/src/App.svelte','frontend/src/ProcessHMI.svelte','src/causalverse/dashboard/server.py']
    monkeypatch.setattr(protection,'verify',lambda:dict(test_fixture_only=True,changed_hashes=changed.copy(),missing_files=[],unreadable_files=[],verification_errors=[]))
    real_sha=protection.sha
    monkeypatch.setattr(protection,'sha',lambda path:'not-approved' if tampered and str(path).endswith('App.svelte') else real_sha(path))
    monkeypatch.setattr(main,'make_main_server',lambda *args,**kwargs:StopAfterAdmission())
    monkeypatch.setattr('sys.argv',['server','--port','8768'])
    with pytest.raises(RuntimeError,match='UNEXPECTED_PROTECTED_CHANGE' if tampered else 'ADMISSION_PASSED_TEST_ONLY'):main.main()
