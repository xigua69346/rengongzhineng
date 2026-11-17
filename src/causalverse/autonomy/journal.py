"""Exclusive append-only hash chain. Cursor recovery never resumes a dead plant."""
import json,os
from pathlib import Path
from datetime import datetime,timezone
from .contracts import digest

class Journal:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.fp=self.path.open('x',encoding='utf-8');self.seq=0;self.previous=None
    def append(self,kind,payload):
        record=dict(seq=self.seq,kind=kind,payload=payload,previous_hash=self.previous,
                    written_at_utc=datetime.now(timezone.utc).isoformat())
        record['record_hash']=digest(record)
        self.fp.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n');self.fp.flush()
        if self.seq%60==0:os.fsync(self.fp.fileno())
        self.previous=record['record_hash'];self.seq+=1;return record
    def close(self):
        if not self.fp.closed:self.fp.flush();os.fsync(self.fp.fileno());self.fp.close()

def read_verified(path,after=-1,allow_partial=False):
    previous=None;records=[]
    with Path(path).open(encoding='utf-8') as f:
        for seq,line in enumerate(f):
            if not line.endswith('\n'):
                if allow_partial:break
                raise ValueError('JOURNAL_TRUNCATED')
            r=json.loads(line)
            if r['seq']!=seq or r['previous_hash']!=previous or r['record_hash']!=digest({k:v for k,v in r.items() if k!='record_hash'}):
                raise ValueError('JOURNAL_INTEGRITY')
            previous=r['record_hash']
            if seq>after:records.append(r)
    return records
