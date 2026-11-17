"""Automatic event policy observes detector outputs only, never fault truth."""
from .contracts import digest,X_COLUMNS

class Events:
    def __init__(self,episode,confirmations=2):
        self.episode=episode;self.confirmations=confirmations;self.active=None;self.streak=0
        self.total_scores=0;self.alarm_scores=0
    def update(self,result):
        a=result['arrays'];t=result['observation_time'][-1]
        alarm=bool(a['pred_PCA'][-1] or a['pred_Threshold'][-1]);self.total_scores+=1
        if alarm:
            self.alarm_scores+=1;self.streak+=1
            if self.active is None:
                self.active=dict(event_id=digest([self.episode,t]),episode_id=self.episode,first_alarm_time=t)
            self.active.update(status='CONFIRMED' if self.streak>=self.confirmations else 'CANDIDATE',
                latest_time=t,consecutive_alarms=self.streak,
                evidence_hash=digest(result),model_version=result['model_version'],
                variables=[X_COLUMNS[i] for i in sorted(range(41),key=lambda i:a['SPE_contribution'][-1][i],reverse=True)[:5]],
                variable_semantics='SPE_CONTRIBUTION_NOT_ROOT_CAUSE',policy='pca_or_threshold_consecutive_2_v1',
                diagnosis_status='NOT_IMPLEMENTED_S4',optimization_allowed=False)
            return dict(self.active)
        self.streak=0
        if self.active:
            r=dict(self.active,status='CLEARED',latest_time=t);self.active=None;return r
        return dict(status='NOT_TRIGGERED',episode_id=self.episode,latest_time=t,
                    truth_evaluation='NOT_EVALUATED_ONLINE_NO_LABEL_ACCESS')
