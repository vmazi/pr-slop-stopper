"""PR acceptance rate heuristic implementation."""

from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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


class PRAcceptanceRateHeuristic(BaseHeuristic):
    """Evaluates PR acceptance/merge rate to detect spam patterns.

    Looks at the user's PR history over the last 12 months to identify:
    - High merge rate (positive signal)
    - Low merge rate with high volume (spam signal)
    - Spam months (>10 PRs with <20% merge rate)
    """

    @property
    def name(self) -> str:
        return "pr_acceptance_rate"

    def evaluate(
        self,
        user: "GitHubUserProtocol",
        *,
        reference_date: datetime | None = None,
        github_client: "Github | None" = None,
    ) -> HeuristicResult:
        """Evaluate PR acceptance rate score.

        Args:
            user: GitHub user object
            reference_date: Date to calculate from (default: now UTC)
            github_client: GitHub client for API calls (required for this heuristic)

        Returns:
            HeuristicResult with PR acceptance rate score
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        # If no client provided, return neutral score
        if github_client is None:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_client": 0},
                details={"error": "GitHub client required for PR analysis"},
            )

        # Calculate date range (last 12 months)
        start_date = reference_date - relativedelta(months=12)

        # Search for user's PRs
        try:
            prs = self._fetch_user_prs(github_client, user.login, start_date)
        except Exception:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"api_error": 0},
                details={"error": "Failed to fetch PR data"},
            )

        return self._calculate_score(prs, reference_date)

    def _fetch_user_prs(
        self,
        client: "Github",
        username: str,
        start_date: datetime,
    ) -> list[dict]:
        """Fetch user's PRs from the last 12 months.

        Args:
            client: GitHub API client
            username: GitHub username
            start_date: Start of date range

        Returns:
            List of PR data dictionaries
        """
        # Format date for GitHub search
        date_str = start_date.strftime("%Y-%m-%d")
        query = f"author:{username} is:pr created:>={date_str}"

        prs = []
        results = client.search_issues(query)

        for pr in results:
            prs.append(
                {
                    "number": pr.number,
                    "state": pr.state,
                    "merged": getattr(pr, "pull_request", {}).get("merged_at") is not None
                    if hasattr(pr, "pull_request") and pr.pull_request
                    else pr.state == "closed",
                    "created_at": pr.created_at,
                    "repository": pr.repository.full_name if pr.repository else "unknown",
                }
            )

        return prs

    def _calculate_score(
        self,
        prs: list[dict],
        reference_date: datetime,
    ) -> HeuristicResult:
        """Calculate score based on PR data.

        Args:
            prs: List of PR data dictionaries
            reference_date: Reference date for calculations

        Returns:
            HeuristicResult with calculated score
        """
        score = 0
        breakdown: dict[str, int] = {}
        details: dict[str, DetailValue] = {
            "total_prs": len(prs),
            "merged_prs": 0,
            "closed_prs": 0,
            "open_prs": 0,
            "merge_rate": 0.0,
            "spam_months": 0,
            "unique_repos": 0,
        }

        if not prs:
            # No PRs - neutral, but slightly negative for very new accounts
            details["merge_rate"] = None
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_prs": 0},
                details=details,
            )

        # Count PR states
        merged = sum(1 for pr in prs if pr.get("merged"))
        closed = sum(1 for pr in prs if pr.get("state") == "closed" and not pr.get("merged"))
        open_prs = sum(1 for pr in prs if pr.get("state") == "open")

        details["merged_prs"] = merged
        details["closed_prs"] = closed
        details["open_prs"] = open_prs

        # Calculate overall merge rate (merged / (merged + closed))
        completed = merged + closed
        if completed > 0:
            merge_rate = merged / completed
            details["merge_rate"] = round(merge_rate * 100, 1)
        else:
            merge_rate = 0.0
            details["merge_rate"] = 0.0

        # Count unique repos
        unique_repos = len({pr.get("repository", "unknown") for pr in prs})
        details["unique_repos"] = unique_repos

        # Positive signal: High merge rate
        if merge_rate >= 0.8 and merged >= 5:
            score += 10
            breakdown["high_merge_rate"] = 10
        elif merge_rate >= 0.6 and merged >= 3:
            score += 5
            breakdown["good_merge_rate"] = 5

        # Negative signal: Low merge rate with high volume
        if len(prs) >= 20 and merge_rate < 0.3:
            score -= 15
            breakdown["low_merge_high_volume"] = -15
        elif len(prs) >= 10 and merge_rate < 0.2:
            score -= 10
            breakdown["very_low_merge_rate"] = -10

        # Check for spam months (>10 PRs with <20% merge rate in a single month)
        spam_months = self._detect_spam_months(prs)
        details["spam_months"] = spam_months

        if spam_months >= 3:
            score -= 25
            breakdown["multiple_spam_months"] = -25
        elif spam_months >= 1:
            score -= 10
            breakdown["spam_month_detected"] = -10

        # Negative signal: PRs to many different repos (spray pattern)
        if unique_repos >= 20 and merge_rate < 0.3:
            score -= 10
            breakdown["spray_pattern"] = -10

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )

    def _detect_spam_months(self, prs: list[dict]) -> int:
        """Detect months with spam-like PR patterns.

        A spam month is defined as >10 PRs with <20% merge rate.

        Args:
            prs: List of PR data

        Returns:
            Number of spam months detected
        """
        # Group PRs by month
        monthly_prs: dict[str, list[dict]] = defaultdict(list)

        for pr in prs:
            created = pr.get("created_at")
            if created:
                if isinstance(created, datetime):
                    month_key = created.strftime("%Y-%m")
                else:
                    month_key = str(created)[:7]  # "YYYY-MM" format
                monthly_prs[month_key].append(pr)

        # Check each month for spam pattern
        spam_months = 0
        for month_prs in monthly_prs.values():
            if len(month_prs) > 10:
                merged = sum(1 for pr in month_prs if pr.get("merged"))
                closed = sum(
                    1 for pr in month_prs if pr.get("state") == "closed" and not pr.get("merged")
                )
                completed = merged + closed

                if completed > 0:
                    merge_rate = merged / completed
                    if merge_rate < 0.2:
                        spam_months += 1

        return spam_months


# Register the heuristic
registry.register(PRAcceptanceRateHeuristic())
