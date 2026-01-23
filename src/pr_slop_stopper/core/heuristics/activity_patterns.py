"""Activity patterns heuristic implementation."""

from collections import defaultdict
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from github import Github

from pr_slop_stopper.core.heuristics.base import (
    BaseHeuristic,
    DetailValue,
    HeuristicResult,
    registry,
)
from pr_slop_stopper.types import GitHubUserProtocol


class ActivityPatternsHeuristic(BaseHeuristic):
    """Evaluates activity patterns to detect suspicious behavior.

    Looks at temporal patterns in user's GitHub activity to identify:
    - Consistent contribution history (positive signal)
    - Burst activity followed by silence (potential bot/spam signal)
    - Activity concentrated in specific time windows
    - Recent account activation after dormancy
    """

    @property
    def name(self) -> str:
        return "activity_patterns"

    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> HeuristicResult:
        """Evaluate activity pattern score.

        Args:
            user: GitHub user object
            reference_date: Date to calculate from (default: now UTC)
            github_client: GitHub client for API calls

        Returns:
            HeuristicResult with activity pattern score
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        if github_client is None:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_client": 0},
                details={"error": "GitHub client required for activity analysis"},
            )

        try:
            activity_data = self._fetch_activity_data(github_client, user.login, reference_date)
        except Exception:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"api_error": 0},
                details={"error": "Failed to fetch activity data"},
            )

        return self._calculate_score(activity_data, reference_date)

    def _fetch_activity_data(
        self,
        client: Github,
        username: str,
        reference_date: datetime,
    ) -> dict:
        """Fetch activity data from user's events and PRs.

        Args:
            client: GitHub API client
            username: GitHub username
            reference_date: Reference date for calculations

        Returns:
            Dictionary with activity statistics
        """
        start_date = reference_date - relativedelta(months=12)
        date_str = start_date.strftime("%Y-%m-%d")

        # Get PRs from last 12 months
        query = f"author:{username} is:pr created:>={date_str}"
        results = client.search_issues(query)

        # Group by month and day of week
        monthly_activity: dict[str, int] = defaultdict(int)
        daily_activity: dict[int, int] = defaultdict(int)  # 0=Monday, 6=Sunday
        hourly_activity: dict[int, int] = defaultdict(int)
        pr_dates: list[datetime] = []

        for pr in results:
            created_at = pr.created_at
            if created_at:
                pr_dates.append(created_at)
                month_key = created_at.strftime("%Y-%m")
                monthly_activity[month_key] += 1
                daily_activity[created_at.weekday()] += 1
                hourly_activity[created_at.hour] += 1

        return {
            "monthly_activity": dict(monthly_activity),
            "daily_activity": dict(daily_activity),
            "hourly_activity": dict(hourly_activity),
            "pr_dates": pr_dates,
            "total_prs": len(pr_dates),
        }

    def _calculate_score(
        self,
        activity_data: dict,
        reference_date: datetime,
    ) -> HeuristicResult:
        """Calculate score based on activity patterns.

        Args:
            activity_data: Activity statistics
            reference_date: Reference date

        Returns:
            HeuristicResult with calculated score
        """
        score = 0
        breakdown: dict[str, int] = {}
        details: dict[str, DetailValue] = {
            "total_prs": activity_data.get("total_prs", 0),
            "active_months": 0,
            "burst_detected": False,
            "consistent_activity": False,
            "weekend_ratio": 0.0,
            "night_ratio": 0.0,
        }

        total_prs = activity_data.get("total_prs", 0)
        if total_prs == 0:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_activity": 0},
                details=details,
            )

        monthly = activity_data.get("monthly_activity", {})
        daily = activity_data.get("daily_activity", {})
        hourly = activity_data.get("hourly_activity", {})
        pr_dates = activity_data.get("pr_dates", [])

        # Count active months
        active_months = len([m for m in monthly.values() if m > 0])
        details["active_months"] = active_months

        # Check for consistent activity (positive signal)
        if active_months >= 6 and total_prs >= 10:
            score += 10
            breakdown["consistent_contributor"] = 10
            details["consistent_activity"] = True
        elif active_months >= 3 and total_prs >= 5:
            score += 5
            breakdown["regular_contributor"] = 5

        # Check for burst activity (potential spam signal)
        burst_score = self._detect_burst_pattern(monthly, total_prs)
        if burst_score < 0:
            score += burst_score
            breakdown["burst_activity"] = burst_score
            details["burst_detected"] = True

        # Weekend activity ratio
        weekend_prs = daily.get(5, 0) + daily.get(6, 0)  # Saturday + Sunday
        weekend_ratio = weekend_prs / total_prs if total_prs > 0 else 0
        details["weekend_ratio"] = round(weekend_ratio * 100, 1)

        # Night activity ratio (midnight to 6am)
        night_prs = sum(hourly.get(h, 0) for h in range(0, 6))
        night_ratio = night_prs / total_prs if total_prs > 0 else 0
        details["night_ratio"] = round(night_ratio * 100, 1)

        # Suspicious: Very high concentration in single time window
        if night_ratio >= 0.8 and total_prs >= 10:
            score -= 10
            breakdown["suspicious_timing"] = -10

        # Check for recent activation after long dormancy
        dormancy_penalty = self._check_dormancy_pattern(pr_dates, reference_date)
        if dormancy_penalty < 0:
            score += dormancy_penalty
            breakdown["dormancy_spike"] = dormancy_penalty

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )

    def _detect_burst_pattern(
        self,
        monthly: dict[str, int],
        total_prs: int,
    ) -> int:
        """Detect burst activity patterns.

        Args:
            monthly: Monthly PR counts
            total_prs: Total PR count

        Returns:
            Negative score if burst pattern detected, 0 otherwise
        """
        if total_prs < 10 or len(monthly) < 2:
            return 0

        # Check if >70% of PRs are in a single month
        max_month = max(monthly.values()) if monthly else 0
        if max_month / total_prs >= 0.7:
            return -15

        # Check if >80% of PRs are in 2 months
        sorted_months = sorted(monthly.values(), reverse=True)
        if len(sorted_months) >= 2:
            top_two = sorted_months[0] + sorted_months[1]
            if top_two / total_prs >= 0.8:
                return -10

        return 0

    def _check_dormancy_pattern(
        self,
        pr_dates: list[datetime],
        reference_date: datetime,
    ) -> int:
        """Check for recent activation after long dormancy.

        Args:
            pr_dates: List of PR creation dates
            reference_date: Reference date

        Returns:
            Negative score if suspicious dormancy pattern, 0 otherwise
        """
        if len(pr_dates) < 5:
            return 0

        # Sort dates
        sorted_dates = sorted(pr_dates)

        # Check gap between oldest and second oldest PR
        # If huge gap followed by sudden burst, that's suspicious
        if len(sorted_dates) >= 10:
            # Calculate gaps between consecutive PRs
            gaps = []
            for i in range(1, len(sorted_dates)):
                gap = (sorted_dates[i] - sorted_dates[i - 1]).days
                gaps.append(gap)

            # Find max gap
            max_gap = max(gaps) if gaps else 0

            # If there's a gap of >90 days followed by many PRs, suspicious
            if max_gap > 90:
                # Count PRs after the gap
                gap_index = gaps.index(max_gap)
                prs_after_gap = len(sorted_dates) - gap_index - 1

                if prs_after_gap >= 8:
                    return -10

        return 0


# Register the heuristic
registry.register(ActivityPatternsHeuristic())
