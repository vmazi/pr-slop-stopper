"""Tests for notable OSS contributions heuristic."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pr_slop_stopper.core.heuristics.notable_contributions import (
    NotableContributionsHeuristic,
)


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.login = login
    return user


def make_mock_issue_with_repo(repo_name: str, stars: int) -> MagicMock:
    """Create a mock issue with repository."""
    issue = MagicMock()
    repo = MagicMock()
    repo.full_name = repo_name
    repo.stargazers_count = stars
    issue.repository = repo
    return issue


class TestNotableContributionsHeuristic:
    """Tests for NotableContributionsHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = NotableContributionsHeuristic()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "notable_contributions"

    def test_no_client_returns_neutral(self) -> None:
        """Test that no client returns neutral score with error."""
        user = make_mock_user()
        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 0
        assert "no_client" in result.breakdown
        assert "error" in result.details

    def test_no_merged_prs_returns_neutral(self) -> None:
        """Test that user with no merged PRs gets neutral score."""
        user = make_mock_user()
        client = MagicMock()
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert result.details["total_merged_prs"] == 0

    def test_very_popular_contributor_high_score(self) -> None:
        """Test that contributor to very popular repos gets high score."""
        user = make_mock_user()
        client = MagicMock()

        # Contributions to 3 very popular repos (10k+ stars)
        issues = [
            make_mock_issue_with_repo("facebook/react", 200000),
            make_mock_issue_with_repo("microsoft/vscode", 150000),
            make_mock_issue_with_repo("kubernetes/kubernetes", 100000),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score >= 20
        assert "very_popular_contributor" in result.breakdown
        assert result.details["very_popular_repo_count"] == 3

    def test_single_very_popular_contribution(self) -> None:
        """Test that single very popular contribution gets moderate score."""
        user = make_mock_user()
        client = MagicMock()

        issues = [
            make_mock_issue_with_repo("facebook/react", 200000),
            make_mock_issue_with_repo("someorg/small-repo", 50),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "has_very_popular_contribution" in result.breakdown

    def test_popular_contributor_positive_score(self) -> None:
        """Test that contributor to popular repos gets positive score."""
        user = make_mock_user()
        client = MagicMock()

        # Contributions to 5 popular repos (1k+ stars)
        issues = [make_mock_issue_with_repo(f"org/repo{i}", 2000 + i * 100) for i in range(5)]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "popular_contributor" in result.breakdown
        assert result.details["popular_repo_count"] == 5

    def test_few_popular_contributions(self) -> None:
        """Test that few popular contributions get smaller score."""
        user = make_mock_user()
        client = MagicMock()

        issues = [
            make_mock_issue_with_repo("org/repo1", 2000),
            make_mock_issue_with_repo("org/repo2", 3000),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "has_popular_contributions" in result.breakdown

    def test_diverse_notable_contributions(self) -> None:
        """Test that diverse notable contributions get score."""
        user = make_mock_user()
        client = MagicMock()

        # Contributions to 6 notable repos (100+ stars)
        issues = [make_mock_issue_with_repo(f"org/notable{i}", 200 + i * 50) for i in range(6)]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "diverse_notable_contributions" in result.breakdown

    def test_only_small_repos_negative(self) -> None:
        """Test that many PRs only to small repos gets negative score."""
        user = make_mock_user()
        client = MagicMock()

        # 25 PRs all to tiny repos
        issues = [make_mock_issue_with_repo(f"user{i}/tiny-repo{i}", 5) for i in range(25)]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "only_small_repos" in result.breakdown

    def test_mixed_contributions_balanced(self) -> None:
        """Test that mixed contributions across repo sizes is balanced."""
        user = make_mock_user()
        client = MagicMock()

        issues = [
            make_mock_issue_with_repo("big/popular", 15000),  # very popular
            make_mock_issue_with_repo("mid/repo1", 2000),  # popular
            make_mock_issue_with_repo("mid/repo2", 1500),  # popular
            make_mock_issue_with_repo("small/repo1", 200),  # notable
            make_mock_issue_with_repo("tiny/repo1", 10),  # small
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        # Should have positive score from popular contributions
        assert result.score > 0
        # Should not have negative penalty since not only small repos
        assert "only_small_repos" not in result.breakdown

    def test_duplicate_repos_counted_once(self) -> None:
        """Test that contributions to same repo are counted once."""
        user = make_mock_user()
        client = MagicMock()

        # 3 PRs to same repo
        issues = [
            make_mock_issue_with_repo("facebook/react", 200000),
            make_mock_issue_with_repo("facebook/react", 200000),
            make_mock_issue_with_repo("facebook/react", 200000),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        # Only 1 unique repo
        assert result.details["very_popular_repo_count"] == 1
        assert result.details["total_merged_prs"] == 3

    def test_api_error_returns_neutral(self) -> None:
        """Test that API errors return neutral score."""
        user = make_mock_user()
        client = MagicMock()
        client.search_issues.side_effect = Exception("API error")

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert "api_error" in result.breakdown

    def test_details_include_all_metrics(self) -> None:
        """Test that details include all expected metrics."""
        user = make_mock_user()
        client = MagicMock()

        issues = [
            make_mock_issue_with_repo("org/repo", 500),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "total_merged_prs" in result.details
        assert "very_popular_repo_count" in result.details
        assert "popular_repo_count" in result.details
        assert "notable_repo_count" in result.details
        assert "small_repo_count" in result.details
