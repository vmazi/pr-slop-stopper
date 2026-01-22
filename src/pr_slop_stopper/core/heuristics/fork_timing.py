"""Fork timing check heuristic implementation."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.heuristics.base import (
    BaseHeuristic,
    DetailValue,
    HeuristicResult,
    registry,
)

if TYPE_CHECKING:
    from github import Github

    from pr_slop_stopper.types import GitHubUserProtocol

# Time thresholds
SUSPICIOUS_FORK_HOURS = 24  # Fork to PR within 24 hours is suspicious
VERY_SUSPICIOUS_FORK_HOURS = 1  # Fork to PR within 1 hour is very suspicious


class ForkTimingHeuristic(BaseHeuristic):
    """Evaluates fork timing patterns to detect spam.

    Looks at the relationship between when repos are forked and when
    PRs are created to identify:
    - Quick fork-to-PR patterns (spam signal)
    - Many quick forks (spray pattern)
    - Established contributor with older forks (positive signal)
    """

    @property
    def name(self) -> str:
        return "fork_timing"

    def evaluate(
        self,
        user: "GitHubUserProtocol",
        *,
        reference_date: datetime | None = None,
        github_client: "Github | None" = None,
    ) -> HeuristicResult:
        """Evaluate fork timing pattern score.

        Args:
            user: GitHub user object
            reference_date: Date to calculate from (default: now UTC)
            github_client: GitHub client for API calls

        Returns:
            HeuristicResult with fork timing score
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        if github_client is None:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_client": 0},
                details={"error": "GitHub client required for fork timing analysis"},
            )

        try:
            timing_data = self._fetch_fork_timing_data(github_client, user.login, reference_date)
        except Exception:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"api_error": 0},
                details={"error": "Failed to fetch fork timing data"},
            )

        return self._calculate_score(timing_data)

    def _fetch_fork_timing_data(
        self,
        client: "Github",
        username: str,
        reference_date: datetime,
    ) -> dict:
        """Fetch fork timing data from user's repos and PRs.

        Args:
            client: GitHub API client
            username: GitHub username
            reference_date: Reference date

        Returns:
            Dictionary with fork timing statistics
        """
        start_date = reference_date - relativedelta(months=12)
        date_str = start_date.strftime("%Y-%m-%d")

        # Get user's forks
        user = client.get_user(username)
        forks: dict[str, datetime] = {}

        for repo in user.get_repos(type="owner"):
            if repo.fork:
                # Get parent repo name
                try:
                    parent = repo.parent
                    if parent:
                        forks[parent.full_name] = repo.created_at
                except Exception:
                    continue

        # Get user's PRs
        query = f"author:{username} is:pr created:>={date_str}"
        results = client.search_issues(query)

        stats: dict[str, Any] = {
            "total_prs": 0,
            "prs_with_fork_data": 0,
            "very_quick_fork_prs": 0,  # < 1 hour
            "quick_fork_prs": 0,  # < 24 hours
            "established_fork_prs": 0,  # Fork existed > 7 days before PR
            "fork_to_pr_times": [],  # Hours between fork and PR
        }

        for issue in results:
            stats["total_prs"] = int(stats["total_prs"]) + 1

            try:
                repo = issue.repository
                if repo is None:
                    continue

                repo_name = repo.full_name
                pr_created = issue.created_at

                # Check if we have fork data for this repo
                if repo_name in forks:
                    stats["prs_with_fork_data"] = int(stats["prs_with_fork_data"]) + 1
                    fork_time = forks[repo_name]

                    # Calculate time between fork and PR
                    if pr_created and fork_time:
                        delta = pr_created - fork_time
                        hours = delta.total_seconds() / 3600

                        fork_times = stats["fork_to_pr_times"]
                        if isinstance(fork_times, list):
                            fork_times.append(hours)

                        if hours < VERY_SUSPICIOUS_FORK_HOURS:
                            stats["very_quick_fork_prs"] = int(stats["very_quick_fork_prs"]) + 1
                        elif hours < SUSPICIOUS_FORK_HOURS:
                            stats["quick_fork_prs"] = int(stats["quick_fork_prs"]) + 1
                        elif hours >= 24 * 7:  # > 7 days
                            stats["established_fork_prs"] = int(stats["established_fork_prs"]) + 1

            except Exception:
                continue

        return stats

    def _calculate_score(self, stats: dict) -> HeuristicResult:
        """Calculate score based on fork timing statistics.

        Args:
            stats: Fork timing statistics

        Returns:
            HeuristicResult with calculated score
        """
        score = 0
        breakdown: dict[str, int] = {}

        total_prs = stats.get("total_prs", 0)
        prs_with_fork = stats.get("prs_with_fork_data", 0)
        very_quick = stats.get("very_quick_fork_prs", 0)
        quick = stats.get("quick_fork_prs", 0)
        established = stats.get("established_fork_prs", 0)
        fork_times = stats.get("fork_to_pr_times", [])

        if not isinstance(total_prs, int):
            total_prs = 0
        if not isinstance(prs_with_fork, int):
            prs_with_fork = 0
        if not isinstance(very_quick, int):
            very_quick = 0
        if not isinstance(quick, int):
            quick = 0
        if not isinstance(established, int):
            established = 0
        if not isinstance(fork_times, list):
            fork_times = []

        # Calculate average fork-to-PR time
        avg_fork_time = 0.0
        if fork_times:
            avg_fork_time = sum(fork_times) / len(fork_times)

        details: dict[str, DetailValue] = {
            "total_prs": total_prs,
            "prs_with_fork_data": prs_with_fork,
            "very_quick_fork_prs": very_quick,
            "quick_fork_prs": quick,
            "established_fork_prs": established,
            "avg_fork_to_pr_hours": round(avg_fork_time, 1),
        }

        if total_prs == 0:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_prs": 0},
                details=details,
            )

        # Negative: Many very quick fork-to-PR (< 1 hour)
        if very_quick >= 5:
            score -= 20
            breakdown["many_instant_fork_prs"] = -20
        elif very_quick >= 3:
            score -= 15
            breakdown["several_instant_fork_prs"] = -15
        elif very_quick >= 1:
            score -= 5
            breakdown["has_instant_fork_pr"] = -5

        # Negative: Many quick fork-to-PR (< 24 hours)
        if quick >= 10:
            score -= 15
            breakdown["many_quick_fork_prs"] = -15
        elif quick >= 5:
            score -= 10
            breakdown["several_quick_fork_prs"] = -10

        # Positive: Established contributor (PRs from forks > 7 days old)
        if prs_with_fork > 0:
            established_ratio = established / prs_with_fork
            if established_ratio >= 0.8 and established >= 5:
                score += 10
                breakdown["established_contributor"] = 10
            elif established_ratio >= 0.5 and established >= 3:
                score += 5
                breakdown["mostly_established_forks"] = 5

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )


# Register the heuristic
registry.register(ForkTimingHeuristic())
