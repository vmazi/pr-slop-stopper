"""Heuristic implementations for reputation scoring."""

# Import heuristics to register them
from pr_slop_stopper.core.heuristics import (
    account_age,  # noqa: F401
    follower_patterns,  # noqa: F401
    profile_completeness,  # noqa: F401
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
