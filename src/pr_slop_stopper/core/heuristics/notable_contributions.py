"""Notable OSS contributions heuristic implementation."""

from datetime import UTC, datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from github import Github

from pr_slop_stopper.core.heuristics.base import (
    BaseHeuristic,
    DetailValue,
    HeuristicResult,
    registry,
)
from pr_slop_stopper.types import GitHubUserProtocol

# Star thresholds for repo classification
VERY_POPULAR_THRESHOLD = 10000  # 10k+ stars
POPULAR_THRESHOLD = 1000  # 1k+ stars
NOTABLE_THRESHOLD = 100  # 100+ stars


class NotableContributionsHeuristic(BaseHeuristic):
    """Evaluates contributions to notable open source projects.

    Looks at the popularity and reputation of repositories the user
    has contributed to:
    - Contributions to very popular repos (positive signal)
    - Contributions to popular repos (positive signal)
    - Contributions only to tiny/unknown repos (neutral to negative)
    """

    @property
    def name(self) -> str:
        return "notable_contributions"

    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> HeuristicResult:
        """Evaluate notable contributions score.

        Args:
            user: GitHub user object
            reference_date: Date to calculate from (default: now UTC)
            github_client: GitHub client for API calls

        Returns:
            HeuristicResult with notable contributions score
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        if github_client is None:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_client": 0},
                details={"error": "GitHub client required for contribution analysis"},
            )

        try:
            contribution_data = self._fetch_contribution_data(
                github_client, user.login, reference_date
            )
        except Exception:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"api_error": 0},
                details={"error": "Failed to fetch contribution data"},
            )

        return self._calculate_score(contribution_data)

    def _fetch_contribution_data(
        self,
        client: Github,
        username: str,
        reference_date: datetime,
    ) -> dict:
        """Fetch contribution data and repo statistics.

        Args:
            client: GitHub API client
            username: GitHub username
            reference_date: Reference date

        Returns:
            Dictionary with contribution statistics
        """
        start_date = reference_date - relativedelta(months=24)
        date_str = start_date.strftime("%Y-%m-%d")

        # Search for merged PRs by this user
        query = f"author:{username} is:pr is:merged created:>={date_str}"
        results = client.search_issues(query)

        stats: dict[str, Any] = {
            "total_merged_prs": 0,
            "very_popular_repos": [],
            "popular_repos": [],
            "notable_repos": [],
            "small_repos": [],
            "repo_stars": {},
        }

        seen_repos: set[str] = set()

        for issue in results:
            stats["total_merged_prs"] = int(stats["total_merged_prs"]) + 1

            try:
                repo = issue.repository
                if repo is None:
                    continue

                repo_name = repo.full_name
                if repo_name in seen_repos:
                    continue
                seen_repos.add(repo_name)

                # Get repo star count
                stars = repo.stargazers_count

                repo_stars = stats["repo_stars"]
                if isinstance(repo_stars, dict):
                    repo_stars[repo_name] = stars

                # Classify repo by popularity
                if stars >= VERY_POPULAR_THRESHOLD:
                    very_popular = stats["very_popular_repos"]
                    if isinstance(very_popular, list):
                        very_popular.append(repo_name)
                elif stars >= POPULAR_THRESHOLD:
                    popular = stats["popular_repos"]
                    if isinstance(popular, list):
                        popular.append(repo_name)
                elif stars >= NOTABLE_THRESHOLD:
                    notable = stats["notable_repos"]
                    if isinstance(notable, list):
                        notable.append(repo_name)
                else:
                    small = stats["small_repos"]
                    if isinstance(small, list):
                        small.append(repo_name)

            except Exception:
                # Skip repos we can't analyze
                continue

        return stats

    def _calculate_score(self, stats: dict) -> HeuristicResult:
        """Calculate score based on contribution statistics.

        Args:
            stats: Contribution statistics

        Returns:
            HeuristicResult with calculated score
        """
        score = 0
        breakdown: dict[str, int] = {}

        very_popular = stats.get("very_popular_repos", [])
        popular = stats.get("popular_repos", [])
        notable = stats.get("notable_repos", [])
        small = stats.get("small_repos", [])

        if not isinstance(very_popular, list):
            very_popular = []
        if not isinstance(popular, list):
            popular = []
        if not isinstance(notable, list):
            notable = []
        if not isinstance(small, list):
            small = []

        details: dict[str, DetailValue] = {
            "total_merged_prs": stats.get("total_merged_prs", 0),
            "very_popular_repo_count": len(very_popular),
            "popular_repo_count": len(popular),
            "notable_repo_count": len(notable),
            "small_repo_count": len(small),
            "very_popular_repos": very_popular[:5],  # Limit to first 5
            "popular_repos": popular[:5],
        }

        total_merged = stats.get("total_merged_prs", 0)
        if not isinstance(total_merged, int):
            total_merged = 0

        if total_merged == 0:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_merged_prs": 0},
                details=details,
            )

        # Strong positive: Contributions to very popular repos
        if len(very_popular) >= 3:
            score += 20
            breakdown["very_popular_contributor"] = 20
        elif len(very_popular) >= 1:
            score += 15
            breakdown["has_very_popular_contribution"] = 15

        # Positive: Contributions to popular repos
        if len(popular) >= 5:
            score += 10
            breakdown["popular_contributor"] = 10
        elif len(popular) >= 2:
            score += 5
            breakdown["has_popular_contributions"] = 5

        # Positive: Diverse notable contributions
        if len(notable) >= 5:
            score += 5
            breakdown["diverse_notable_contributions"] = 5

        # Negative: Only tiny repos with many PRs (potential spam)
        total_repos = len(very_popular) + len(popular) + len(notable) + len(small)
        if total_repos > 0:
            small_ratio = len(small) / total_repos
            if small_ratio >= 0.9 and total_merged >= 20:
                score -= 10
                breakdown["only_small_repos"] = -10

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )


# Register the heuristic
registry.register(NotableContributionsHeuristic())
