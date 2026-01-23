"""Reputation scoring engine."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from github import Github

from pr_slop_stopper.core.heuristics import HeuristicResult, registry
from pr_slop_stopper.types import GitHubUserProtocol

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Result of reputation scoring for a user."""

    total_score: int
    clamped_score: int
    breakdown: dict[str, int] = field(default_factory=dict)
    heuristic_results: list[HeuristicResult] = field(default_factory=list)
    recommendation: str = "allow"

    def __post_init__(self) -> None:
        """Set recommendation based on clamped score."""
        # These thresholds can be overridden by repo config
        if self.clamped_score <= -25:
            self.recommendation = "close"
        elif self.clamped_score <= -10:
            self.recommendation = "warn"
        else:
            self.recommendation = "allow"


class ReputationScorer:
    """Aggregates heuristic scores into a reputation score."""

    def __init__(
        self,
        *,
        warning_threshold: int = -10,
        close_threshold: int = -25,
        min_score: int = -100,
        max_score: int = 100,
    ) -> None:
        """Initialize the scorer.

        Args:
            warning_threshold: Score at or below which to warn
            close_threshold: Score at or below which to close PR
            min_score: Minimum clamped score
            max_score: Maximum clamped score
        """
        self.warning_threshold = warning_threshold
        self.close_threshold = close_threshold
        self.min_score = min_score
        self.max_score = max_score

    def calculate_score(
        self,
        user: GitHubUserProtocol,
        *,
        enabled_heuristics: list[str] | None = None,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> ScoringResult:
        """Calculate reputation score for a user.

        Args:
            user: GitHub user object (NamedUser or AuthenticatedUser)
            enabled_heuristics: Optional list of heuristic names to use
            reference_date: Optional reference date for calculations
            github_client: GitHub client for API calls (required for some heuristics)

        Returns:
            ScoringResult with total score and breakdown
        """
        logger.info("Starting reputation scoring for user: %s", user.login)

        results = registry.evaluate_all(
            user,
            enabled=enabled_heuristics,
            reference_date=reference_date,
            github_client=github_client,
        )

        total_score = sum(r.score for r in results)
        clamped_score = max(self.min_score, min(self.max_score, total_score))

        breakdown = {r.name: r.score for r in results}

        # Determine recommendation
        if clamped_score <= self.close_threshold:
            recommendation = "close"
        elif clamped_score <= self.warning_threshold:
            recommendation = "warn"
        else:
            recommendation = "allow"

        logger.info(
            "Scoring complete for %s: total=%d, clamped=%d, recommendation=%s",
            user.login,
            total_score,
            clamped_score,
            recommendation,
        )
        logger.info("Score breakdown: %s", breakdown)

        return ScoringResult(
            total_score=total_score,
            clamped_score=clamped_score,
            breakdown=breakdown,
            heuristic_results=results,
            recommendation=recommendation,
        )
