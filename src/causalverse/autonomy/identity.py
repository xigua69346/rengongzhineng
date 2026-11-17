"""Opaque live identities; never aliases a frozen D3 or D511 run."""
import secrets
from .contracts import digest

def episode_identity():
    return dict(episode_id=secrets.token_hex(16),dataset_id='LIVE_TEP_V1',
                source_mode='LIVE_TEP_SIMULATION',optimization_allowed=False,
                sim_execution_allowed=False,physical_execution_allowed=False)

def observation_id(episode,seq):
    return digest(dict(episode_id=episode,seq=seq,schema='live-tep-1'))
