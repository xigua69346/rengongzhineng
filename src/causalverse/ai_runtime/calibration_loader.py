"""Read original Action/Delta joint radii; no calibration or actionwise selection."""
import numpy as np
from causalverse.decision.intervention_calibration import intervals
from .contracts import require


class CalibrationLoader:
    def __init__(self,registry):
        self.registry=registry
        self.protocol=registry.trusted_json('artifacts/d5_1_1/protocol.json')
        self.scales=np.array(self.protocol['mae_limits'],dtype=float)
        require(np.array_equal(self.scales,[.25,.5,5.]),'CONTRACT_MISMATCH','original target scales required')

    def load(self,kind):
        require(kind in ('action','delta'),'MODEL_UNKNOWN','Action/Delta only')
        p=self.registry.load('d511.calibration_'+kind,'D511')
        require(np.isfinite(p['joint']) and p['joint']>0 and np.asarray(p['actionwise']).shape==(3,),
                'CALIBRATION_INVALID','original finite joint radius required')
        return p

    def bounds(self,mean,kind,delta):
        p=self.load(kind)
        require(delta in (0,1,5),'ACTION_UNSUPPORTED','fixed actions only')
        joint,_=intervals(mean,p['joint'],np.array(p['actionwise']),self.scales,(0,1,5).index(delta))
        return dict(lower=joint[0],upper=joint[1],full_width=2*p['joint']*self.scales,
                    joint=p['joint'],actionwise_audit_only=p['actionwise'],
                    calibration_reference=self.registry.entry('d511.calibration_'+kind))
