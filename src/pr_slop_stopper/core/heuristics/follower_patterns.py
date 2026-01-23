"""Follower patterns heuristic implementation."""

from datetime import datetime

from github import Github

from pr_slop_stopper.core.heuristics.base import BaseHeuristic, HeuristicResult, registry
from pr_slop_stopper.types import GitHubUserProtocol


class FollowerPatternsHeuristic(BaseHeuristic):
    """Evaluates follower/following patterns to detect follow-spam."""

    @property
    def name(self) -> str:
        return "follower_patterns"

    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> HeuristicResult:
        """Evaluate follower patterns score.

        Args:
            user: GitHub user object
            reference_date: Not used, but required by base class
            github_client: GitHub client (unused by this heuristic)

        Returns:
            HeuristicResult with follower patterns score
        """
        followers = user.followers
        following = user.following

        score = 0
        breakdown: dict[str, int] = {}

        # Calculate ratio (avoid division by zero)
        if followers > 0:
            ratio: float | None = following / followers
        else:
            ratio = float("inf") if following > 0 else 0.0

        # Positive signals (mutually exclusive - take highest)
        if followers >= 50:
            score += 8
            breakdown["high_followers"] = 8
            tier = "popular"
        elif followers >= 20:
            score += 5
            breakdown["moderate_followers"] = 5
            tier = "recognized"
        elif followers >= 5:
            score += 2
            breakdown["some_followers"] = 2
            tier = "basic"
        else:
            tier = "minimal"

        # Negative signals (can stack with tier)
        # Pattern 1: Following many but almost no followers (follow spam)
        if following >= 500 and followers < 10:
            score -= 10
            breakdown["follow_spam_extreme"] = -10
        # Pattern 2: Very high following/follower ratio
        elif ratio is not None and ratio > 50 and following > 100:
            score -= 8
            breakdown["high_follow_ratio"] = -8

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details={
                "followers": followers,
                "following": following,
                "ratio": round(ratio, 2) if ratio != float("inf") else None,
                "tier": tier,
            },
        )


# Register the heuristic
registry.register(FollowerPatternsHeuristic())
