"""Original complete-history support and all-candidate retrospective audit."""
import numpy as np
from causalverse.decision.intervention_model import ConditionalPredictor,Ridge
from causalverse.decision.action_support import ActionSupport,candidate_disagreement
from .contracts import require


def restore_members(parameters,kind,prefix=''):
    require(kind in ('action','delta'),'MODEL_UNKNOWN','Action/Delta only')
    models=[]
    for i in range(20):
        model=ConditionalPredictor(kind)
        for block in (('model','base') if kind=='delta' else ('model',)):
            ridge=Ridge();n=104 if block=='model' else 33
            for field,shape in [('mean',(n,)),('scale',(n,)),('coef',(n+1,18))]:
                key=f'{prefix}{i}_{block}_{field}'
                require(key in parameters,'MEMBER_PARAMETER_MISSING',key)
                value=parameters[key]
                require(value.shape==shape,'PARAMETER_SHAPE_ERROR',key)
                require(value.dtype==np.dtype('float64') and np.isfinite(value).all(),'NONFINITE_PARAMETER',key)
                if field=='scale':require(np.all(value>0),'PARAMETER_VALUE_ERROR',key)
                setattr(ridge,field,value)
            setattr(model,block,ridge)
        models.append(model)
    return models


class SupportRuntime:
    def __init__(self,registry):
        p=registry.load('d511.support','D511');self.support=ActionSupport()
        for field in ('lower','upper','scale'):setattr(self.support,field,p[field])
        candidates=registry.load('d511.candidate_support','D511')
        require(len(candidates)==880,'MEMBER_PARAMETER_MISSING','all candidate arrays required')
        self.candidates={kind:[restore_members(candidates,kind,f'{kind}_{c}_') for c in (0,4,11,14)]
                         for kind in ('action','delta')}
        self.scales=np.array([.25,.5,5.])

    def evaluate(self,history,delta,command,kind,member_predictions):
        require(member_predictions.shape==(20,6,3) and np.isfinite(member_predictions).all(),
                'MEMBER_OUTPUT_INVALID','all twenty predictions required')
        std=member_predictions.std(0)
        disagreement=float(np.max(std/self.scales))
        checks=[self.support.check(history,delta,120,h,disagreement,radius=None,command=command)
                for h in (10,30,60,120,300,600)]
        predictions=np.array([[m.predict(history,delta,command) for m in members]
                              for members in self.candidates[kind]])
        means=predictions.mean(1)
        span=candidate_disagreement(means,self.scales)
        reasons=list(checks[-1]['reasons'])
        if span>1:reasons.append('candidate_mechanism_disagreement')
        return dict(member_std=std,member_disagreement=disagreement,candidate_members=predictions,
                    candidate_means=means,candidate_normalized_range=span,
                    horizon_checks=checks,base_support=checks[-1],supported=not reasons,reasons=reasons,
                    support_status='SUPPORTED' if not reasons else 'UNSUPPORTED',candidate_audit_status='AUDIT_ONLY',
                    recursive_spectral_radius_status='NOT_APPLICABLE_DIRECT_FINITE_HORIZON',optimization_allowed=False)
