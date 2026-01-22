"""Heuristic implementations for reputation scoring."""

# Import heuristics to register them (side-effect imports)
from pr_slop_stopper.core.heuristics import (
    account_age,
    activity_patterns,
    contribution_type,
    follower_patterns,
    fork_timing,
    notable_contributions,
    pr_acceptance_rate,
    profile_completeness,
)
from pr_slop_stopper.core.heuristics.base import (
    BaseHeuristic,
    HeuristicRegistry,
    HeuristicResult,
    registry,
)

__all__ = [
    "BaseHeuristic",
    "HeuristicRegistry",
    "HeuristicResult",
    "registry",
]
