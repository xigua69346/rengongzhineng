"""Whitelist projection of the existing adapter row, with analyzer freshness."""
from datetime import datetime,timezone
from .contracts import SCHEMA,digest,validate
from .identity import observation_id

class Acquisition:
    def __init__(self,episode):
        self.episode=episode;self.seq=0;self.gas_next=.1;self.product_next=.25
        self.last_gas=0;self.last_product=0

    def collect(self,raw,measurement_clock_hours=None):
        t=raw['t_seconds'];hours=t/3600 if measurement_clock_hours is None else measurement_clock_hours
        gas=t==0 or hours>=self.gas_next
        product=t==0 or hours>=self.product_next
        if t and gas:self.gas_next+=.1;self.last_gas=t
        if t and product:self.product_next+=.25;self.last_product=t
        row=dict(episode_id=self.episode,observation_id=observation_id(self.episode,self.seq),
                 seq=self.seq,measurement_time=t,state_time=raw['state_t_seconds'],
                 wallclock_utc=datetime.now(timezone.utc).isoformat(),
                 measurements=raw['XMEAS'].tolist(),commands=raw['XMV'].tolist(),quality='FINITE_VALIDATED',
                 freshness=dict(continuous_sample_time=t,gas_analyzer_sample_time=self.last_gas,
                     product_analyzer_sample_time=self.last_product,gas_updated=gas,product_updated=product,
                     gas_age_seconds=t-self.last_gas,product_age_seconds=t-self.last_product,
                     analyzer_semantics='DELAYED_SAMPLE_AND_HOLD_NOT_FRESH_EVERY_SECOND'),
                 schema_hash=digest(SCHEMA))
        row['payload_hash']=digest(row);validate(row,self.episode,self.seq);self.seq+=1
        return row
