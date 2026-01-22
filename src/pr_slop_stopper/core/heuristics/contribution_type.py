"""Contribution type patterns heuristic implementation."""

from collections import defaultdict
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

# File extensions for classification
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".cs",
    ".m",
    ".mm",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".vue",
    ".svelte",
    ".sql",
    ".r",
    ".jl",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".xml",
    ".properties",
    ".lock",
}

DOC_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    ".asciidoc",
}

DOC_FILENAMES = {
    "readme",
    "changelog",
    "contributing",
    "license",
    "authors",
    "history",
    "code_of_conduct",
    "security",
    "support",
    "funding",
}


class ContributionTypeHeuristic(BaseHeuristic):
    """Evaluates contribution patterns to detect docs-only spam.

    Looks at the types of files modified in PRs to identify:
    - Healthy mix of code, docs, and config (positive signal)
    - Docs-only contributions (potential spam signal)
    - Trivial changes (typo fixes, minor doc edits)
    """

    @property
    def name(self) -> str:
        return "contribution_type"

    def evaluate(
        self,
        user: "GitHubUserProtocol",
        *,
        reference_date: datetime | None = None,
        github_client: "Github | None" = None,
    ) -> HeuristicResult:
        """Evaluate contribution type patterns.

        Args:
            user: GitHub user object
            reference_date: Date to calculate from (default: now UTC)
            github_client: GitHub client for API calls

        Returns:
            HeuristicResult with contribution type score
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

        start_date = reference_date - relativedelta(months=12)

        try:
            contributions = self._fetch_contribution_data(github_client, user.login, start_date)
        except Exception:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"api_error": 0},
                details={"error": "Failed to fetch contribution data"},
            )

        return self._calculate_score(contributions)

    def _fetch_contribution_data(
        self,
        client: "Github",
        username: str,
        start_date: datetime,
    ) -> dict:
        """Fetch contribution data from user's PRs.

        Args:
            client: GitHub API client
            username: GitHub username
            start_date: Start of date range

        Returns:
            Dictionary with contribution statistics
        """
        date_str = start_date.strftime("%Y-%m-%d")
        query = f"author:{username} is:pr is:merged created:>={date_str}"

        stats: dict[str, Any] = {
            "code_prs": 0,
            "doc_prs": 0,
            "config_prs": 0,
            "mixed_prs": 0,
            "total_prs": 0,
            "trivial_prs": 0,
            "repos_by_type": defaultdict(set),
        }

        results = client.search_issues(query)

        for issue in results:
            stats["total_prs"] = int(stats["total_prs"]) + 1

            # Get PR details to analyze files
            try:
                repo = issue.repository
                if repo is None:
                    continue

                pr = repo.get_pull(issue.number)
                files = list(pr.get_files())

                pr_type = self._classify_pr(files)
                stats[f"{pr_type}_prs"] = int(stats[f"{pr_type}_prs"]) + 1

                # Track if PR is trivial
                if self._is_trivial_pr(files):
                    stats["trivial_prs"] = int(stats["trivial_prs"]) + 1

                # Track contribution types per repo
                repo_name = repo.full_name
                repos_by_type = stats["repos_by_type"]
                if isinstance(repos_by_type, defaultdict):
                    repos_by_type[pr_type].add(repo_name)

            except Exception:
                # Skip PRs we can't analyze
                continue

        return stats

    def _classify_pr(self, files: list) -> str:
        """Classify a PR based on its file types.

        Args:
            files: List of PR files

        Returns:
            Classification: 'code', 'doc', 'config', or 'mixed'
        """
        has_code = False
        has_doc = False
        has_config = False

        for file in files:
            filename = file.filename.lower()
            ext = self._get_extension(filename)
            base_name = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]

            if ext in CODE_EXTENSIONS:
                has_code = True
            elif ext in DOC_EXTENSIONS or base_name in DOC_FILENAMES:
                has_doc = True
            elif ext in CONFIG_EXTENSIONS:
                has_config = True
            else:
                # Unknown file types default to code
                has_code = True

        if has_code and (has_doc or has_config):
            return "mixed"
        elif has_code:
            return "code"
        elif has_doc:
            return "doc"
        elif has_config:
            return "config"
        else:
            return "code"  # Default to code if no files

    def _get_extension(self, filename: str) -> str:
        """Get file extension from filename.

        Args:
            filename: File path or name

        Returns:
            Lowercase extension including dot, or empty string
        """
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1]
        return ""

    def _is_trivial_pr(self, files: list) -> bool:
        """Check if PR appears to be trivial (typo fixes, etc).

        Args:
            files: List of PR files

        Returns:
            True if PR appears trivial
        """
        if len(files) > 3:
            return False

        total_changes = sum(file.changes for file in files)
        return total_changes <= 10

    def _calculate_score(self, stats: dict) -> HeuristicResult:
        """Calculate score based on contribution statistics.

        Args:
            stats: Contribution statistics

        Returns:
            HeuristicResult with calculated score
        """
        score = 0
        breakdown: dict[str, int] = {}
        details: dict[str, DetailValue] = {
            "total_prs": stats.get("total_prs", 0),
            "code_prs": stats.get("code_prs", 0),
            "doc_prs": stats.get("doc_prs", 0),
            "config_prs": stats.get("config_prs", 0),
            "mixed_prs": stats.get("mixed_prs", 0),
            "trivial_prs": stats.get("trivial_prs", 0),
        }

        total = stats.get("total_prs", 0)
        if not isinstance(total, int):
            total = 0

        if total == 0:
            return HeuristicResult(
                name=self.name,
                score=0,
                breakdown={"no_contributions": 0},
                details=details,
            )

        code_prs = stats.get("code_prs", 0)
        doc_prs = stats.get("doc_prs", 0)
        mixed_prs = stats.get("mixed_prs", 0)
        trivial_prs = stats.get("trivial_prs", 0)

        if not isinstance(code_prs, int):
            code_prs = 0
        if not isinstance(doc_prs, int):
            doc_prs = 0
        if not isinstance(mixed_prs, int):
            mixed_prs = 0
        if not isinstance(trivial_prs, int):
            trivial_prs = 0

        code_ratio = (code_prs + mixed_prs) / total
        doc_ratio = doc_prs / total
        trivial_ratio = trivial_prs / total if total > 0 else 0

        details["code_ratio"] = round(code_ratio * 100, 1)
        details["doc_ratio"] = round(doc_ratio * 100, 1)
        details["trivial_ratio"] = round(trivial_ratio * 100, 1)

        # Positive: Meaningful code contributions
        if code_ratio >= 0.7 and total >= 5:
            score += 10
            breakdown["strong_code_contributor"] = 10
        elif code_ratio >= 0.5 and total >= 3:
            score += 5
            breakdown["code_contributor"] = 5

        # Positive: Mixed contributions (code + docs)
        if mixed_prs >= 3:
            score += 5
            breakdown["mixed_contributions"] = 5

        # Negative: Docs-only with high volume
        if doc_ratio >= 0.8 and total >= 10:
            score -= 15
            breakdown["doc_only_spam_pattern"] = -15
        elif doc_ratio >= 0.9 and total >= 5:
            score -= 10
            breakdown["doc_heavy_pattern"] = -10

        # Negative: High trivial ratio
        if trivial_ratio >= 0.8 and total >= 5:
            score -= 10
            breakdown["trivial_spam_pattern"] = -10
        elif trivial_ratio >= 0.6 and total >= 10:
            score -= 5
            breakdown["many_trivial_prs"] = -5

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )


# Register the heuristic
registry.register(ContributionTypeHeuristic())
