"""Fixed D5.1.2 windows; authorized external a0 reconstruction, without changing P0-01."""
from dataclasses import replace
from pathlib import PurePosixPath
import uuid
import numpy as np
from .contracts import ObservationContext, require, validate_observations
from .observation_reader import ObservationReader, seven
from .provenance import context_payload, stable_hash


def validate_window(context, contract, *, origin=3600):
    require(origin == 3600, 'ORIGIN_UNSUPPORTED', 'fixed experimental origin 3600 only')
    require(context.window in (180,600,1800), 'WINDOW_UNSUPPORTED', 'frozen windows only')
    require(context.as_of >= origin + context.window, 'WINDOW_INCOMPLETE', 'wait until half-open window ends')
    validate_observations(context.observation_time, context.values, context.columns, context.units,
                          contract, context.as_of)
    require(np.array_equal(context.observation_time, np.arange(origin,origin+context.window,10)),
            'TIME_GRID_ERROR', 'complete fixed 10-second window required')
    return context


class WindowReader:
    def __init__(self, registry):
        self.registry = registry
        self.reader = ObservationReader(registry)
        self.protocol = registry.trusted_json('artifacts/d5_1_2/protocol.json')
        self.contract = registry.catalog['contracts']['D512']
        self.external = {PurePosixPath(r['folder'].replace('\\','/')).name:r
                         for r in self.protocol['external_runs']}
        require(len(self.external)==80 and self.protocol['nodes']==['T9','C21','P7','U10'],
                'CONTRACT_MISMATCH', 'original external scope and columns required')

    def read(self, data_ref, *, window, as_of, origin=3600):
        require(origin==3600, 'ORIGIN_UNSUPPORTED', 'no alarm/label-derived start')
        require(type(window) is int and window in self.protocol['windows'], 'WINDOW_UNSUPPORTED', 'frozen windows only')
        require(isinstance(as_of,(int,float)) and np.isfinite(as_of) and as_of>=0,
                'INPUT_SCHEMA_ERROR','finite server as_of required')
        identity, record, folder, path = self.reader.identities.resolve(data_ref)
        if identity.dataset_id=='D3':
            context=self.reader.read(data_ref,'D512',as_of=as_of,window=window)
        else:
            name=identity.branch_id
            require(name in self.external and self.external[name]==record and record['delta']==0 and record['split']=='test',
                    'DATASET_SCOPE_UNVERIFIED','only original protocol external a0 branches')
            require(as_of>=3600+window,'WINDOW_INCOMPLETE','external window incomplete')
            t,x,u=self.reader._raw(path)
            visible=t<=as_of
            t,x,u=t[visible],x[visible],u[visible]
            grid=t%10==0
            values=seven(x[grid],u[grid])
            # Same column-select-copy-then-row-slice layout as frozen training.
            values=values[:,[0,1,2,5]].copy()
            values=values[360:360+window//10]
            times=t[grid][360:360+window//10]
            values.setflags(write=False)
            paths=[path,folder+'/manifest.json','artifacts/d5_1_1/data_log.json',
                   'artifacts/d5_1_1/protocol.json','artifacts/d5_1_2/protocol.json']
            context=ObservationContext(uuid.uuid4().hex,identity.dataset_id,identity.run_id,identity.split,
                identity.branch_id,identity.parent_run_id,identity.snapshot_id,as_of,tuple(times.tolist()),window,
                None,tuple(self.contract['columns']),tuple(self.contract['units']),values,None,
                self.reader.identities.source_digest(paths),'',stable_hash(self.contract))
            context=replace(context,input_hash=stable_hash(context_payload(context)))
        return validate_window(context,self.contract,origin=origin)
