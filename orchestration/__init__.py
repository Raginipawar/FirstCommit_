"""
Person 3's component: Orchestration & Memory.

Public surface:

    from orchestration.agent import SiteAgent, ShareRoundResult
    from orchestration.loop import run_swarm_cycle, SwarmCycleResult

See orchestration/README.md for the full task list, the reference loop
this wraps, and what's still missing to make it a live, Strands/OpenSearch-
backed system rather than one deterministic in-process run.
"""

from .agent import ShareRoundResult, SiteAgent
from .loop import SwarmCycleResult, run_swarm_cycle

__all__ = ["SiteAgent", "ShareRoundResult", "SwarmCycleResult", "run_swarm_cycle"]
