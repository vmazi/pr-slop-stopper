"""Base classes for heuristic implementations."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from github import Github

from pr_slop_stopper.types import GitHubUserProtocol

logger = logging.getLogger(__name__)

# Type alias for details values
DetailValue = str | int | float | bool | None | list[str]


@dataclass
class HeuristicResult:
    """Result from a heuristic evaluation."""

    name: str
    score: int
    breakdown: dict[str, int] = field(default_factory=dict)
    details: dict[str, DetailValue] = field(default_factory=dict)


class BaseHeuristic(ABC):
    """Abstract base class for all heuristics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the heuristic name."""
        ...

    @abstractmethod
    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> HeuristicResult:
        """Evaluate the heuristic for a user.

        Args:
            user: GitHub user object (NamedUser or AuthenticatedUser)
            reference_date: Optional reference date for calculations
            github_client: GitHub client for API calls (required for some heuristics)

        Returns:
            HeuristicResult with score and breakdown
        """
        ...


class HeuristicRegistry:
    """Registry for managing heuristics."""

    def __init__(self) -> None:
        self._heuristics: dict[str, BaseHeuristic] = {}

    def register(self, heuristic: BaseHeuristic) -> None:
        """Register a heuristic."""
        self._heuristics[heuristic.name] = heuristic

    def get(self, name: str) -> BaseHeuristic | None:
        """Get a heuristic by name."""
        return self._heuristics.get(name)

    def all(self) -> list[BaseHeuristic]:
        """Get all registered heuristics."""
        return list(self._heuristics.values())

    def names(self) -> list[str]:
        """Get all heuristic names."""
        return list(self._heuristics.keys())

    def evaluate_all(
        self,
        user: GitHubUserProtocol,
        enabled: list[str] | None = None,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> list[HeuristicResult]:
        """Evaluate all (or specified) heuristics for a user.

        Args:
            user: GitHub user object (NamedUser or AuthenticatedUser)
            enabled: Optional list of heuristic names to evaluate (default: all)
            reference_date: Optional reference date for calculations
            github_client: GitHub client for API calls (required for some heuristics)

        Returns:
            List of HeuristicResult objects
        """
        results = []
        heuristics = self.all() if enabled is None else [h for h in self.all() if h.name in enabled]
        for heuristic in heuristics:
            logger.info("Evaluating heuristic: %s", heuristic.name)
            result = heuristic.evaluate(
                user,
                reference_date=reference_date,
                github_client=github_client,
            )
            logger.info(
                "Heuristic %s: score=%d, details=%s",
                result.name,
                result.score,
                result.details,
            )
            results.append(result)
        return results


# Global registry instance
registry = HeuristicRegistry()
