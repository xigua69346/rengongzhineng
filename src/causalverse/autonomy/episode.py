"""One isolated production process per episode; original PI is the only controller."""
import multiprocessing as mp
import queue,secrets,threading,time,traceback
from collections import deque
from pathlib import Path
from causalverse.simulation import TEPAdapter
from .identity import episode_identity
from .acquisition import Acquisition
from .detection_bridge import DetectionBridge
from .events import Events
from .journal import Journal

def produce(identity,folder,commands,output,heartbeat):
    journal=Journal(Path(folder)/'events.jsonl');status='STARTING';started=time.monotonic()
    def emit(kind,data):
        record=journal.append(kind,data);output.put(record,timeout=5)
    try:
        sim=TEPAdapter();acq=Acquisition(identity['episode_id']);detector=DetectionBridge()
        events=Events(identity['episode_id']);values=[];times=[];paused=False;rate=1.;limit=14400
        emit('lifecycle',dict(identity,status=status))
        target=time.monotonic()
        while sim.t_seconds<limit:
            heartbeat.value=time.monotonic()
            while True:
                try:c=commands.get_nowait()
                except queue.Empty:break
                if c['op']=='stop':status='STOPPED';return
                if c['op']=='pause':paused=True
                if c['op']=='resume':paused=False;target=time.monotonic()
                if c['op']=='configure':rate=c['rate'];limit=c['limit']
                if c['op']=='operator_fault':
                    sim.inject_fault(c['fault_id'])
                    private=Path(folder)/'_private';private.mkdir(exist_ok=True)
                    with (private/(secrets.token_hex(12)+'.json')).open('x',encoding='utf-8') as f:
                        import json
                        json.dump(dict(operator_fault_id=c['fault_id'],requested_at=sim.t_seconds),f)
            if paused:
                if status!='PAUSED':status='PAUSED';emit('lifecycle',dict(status=status))
                time.sleep(.05);continue
            if status!='RUNNING':status='RUNNING';emit('lifecycle',dict(status=status))
            clock=sim.sim.time
            row=acq.collect(sim.step(),clock);emit('observation',row)
            t=row['measurement_time']
            if t>=1800 and t%180==0:
                values.append(row['measurements']);times.append(t)
                result=detector.score(values,times,identity['episode_id']);emit('inference',result)
                emit('anomaly_event',events.update(result))
            if sim.termination_reason:raise RuntimeError(sim.termination_reason)
            # The adapter's row history is not process state; persisted public rows are retained in the journal.
            sim.rows.clear()
            target+=1/rate
            delay=target-time.monotonic()
            if delay>0:time.sleep(min(delay,1))
        status='COMPLETED'
    except Exception as ex:
        status='FAILED'
        try:emit('failure',dict(reason=type(ex).__name__,detail=str(ex),traceback=traceback.format_exc()))
        except Exception:pass
    finally:
        try:emit('lifecycle',dict(status=status,wall_seconds=time.monotonic()-started))
        finally:journal.close()

class Episode:
    def __init__(self,root,owner,rate=1,limit=14400):
        if type(rate) not in (int,float) or rate not in (1,20,100,500):raise ValueError('RATE')
        if type(limit) is not int or not 1<=limit<=14400:raise ValueError('LIMIT')
        self.identity=episode_identity();self.owner=owner;self.folder=Path(root)/self.identity['episode_id']
        self.folder.mkdir(parents=True,exist_ok=False);self.records=deque(maxlen=5000);self.lock=threading.Lock()
        self.status='STARTING';self.started=time.monotonic();self.last_observation=None
        self.ctx=mp.get_context('spawn');self.commands=self.ctx.Queue();self.output=self.ctx.Queue(maxsize=128)
        self.heartbeat=self.ctx.Value('d',time.monotonic());self.commands.put(dict(op='configure',rate=rate,limit=limit))
        self.process=self.ctx.Process(target=produce,args=(self.identity,str(self.folder),self.commands,self.output,self.heartbeat),daemon=True)
        self.process.start();self.thread=threading.Thread(target=self._consume,daemon=True);self.thread.start()
    def _consume(self):
        while self.process.is_alive() or not self.output.empty():
            try:r=self.output.get(timeout=.25)
            except queue.Empty:
                if time.monotonic()-self.heartbeat.value>15:
                    self.process.terminate();self.status='FAILED_WORKER_HEARTBEAT'
                continue
            with self.lock:
                self.records.append(r)
                if r['kind']=='lifecycle':self.status=r['payload']['status']
                if r['kind']=='observation':self.last_observation=r['payload']
        if self.status not in ('STOPPED','COMPLETED','FAILED','FAILED_WORKER_HEARTBEAT'):self.status='UNAVAILABLE_PROCESS_EXIT'
        import json
        with (self.folder/'supervisor_exit.json').open('x',encoding='utf-8') as f:
            json.dump(dict(status=self.status,exitcode=self.process.exitcode),f)
    def control(self,op):
        if op not in ('pause','resume','stop'):raise ValueError('CONTROL_OPERATION')
        self.commands.put(dict(op=op))
    def inject_fault(self,fault_id):
        if type(fault_id) is not int or fault_id not in (4,11,14):raise ValueError('FAULT_SCOPE')
        self.commands.put(dict(op='operator_fault',fault_id=fault_id))
    def view(self,after=-1):
        if type(after) is not int or after< -1:raise ValueError('CURSOR')
        with self.lock:
            records=list(self.records);rows=[r for r in records if r['seq']>after];last=self.last_observation
        gap=bool(rows and rows[0]['seq']>after+1)
        if gap:
            from .journal import read_verified
            rows=read_verified(self.folder/'events.jsonl',after,allow_partial=self.process.is_alive())[:5000]
        return dict(identity=self.identity,status=self.status,wall_seconds=time.monotonic()-self.started,
                    actual_rate=(last['state_time'] if last else 0)/max(.001,time.monotonic()-self.started),
                    latest=last,records=rows,cursor_gap=bool(rows and rows[0]['seq']>after+1),
                    detection_status='WAITING_WARMUP_OR_180S_GRID' if not any(r['kind']=='inference' for r in records) else 'INFERRED',
                    truth_evaluation='UNAVAILABLE_ONLINE',optimization_allowed=False)
