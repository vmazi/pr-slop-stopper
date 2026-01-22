"""Tests for fork timing check heuristic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from pr_slop_stopper.core.heuristics.fork_timing import ForkTimingHeuristic


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.login = login
    return user


def make_mock_fork(parent_name: str, created_at: datetime) -> MagicMock:
    """Create a mock fork repository."""
    repo = MagicMock()
    repo.fork = True
    repo.created_at = created_at
    parent = MagicMock()
    parent.full_name = parent_name
    repo.parent = parent
    return repo


def make_mock_non_fork() -> MagicMock:
    """Create a mock non-fork repository."""
    repo = MagicMock()
    repo.fork = False
    return repo


def make_mock_issue(repo_name: str, created_at: datetime) -> MagicMock:
    """Create a mock issue/PR."""
    issue = MagicMock()
    issue.created_at = created_at
    repo = MagicMock()
    repo.full_name = repo_name
    issue.repository = repo
    return issue


class TestForkTimingHeuristic:
    """Tests for ForkTimingHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = ForkTimingHeuristic()
        self.reference_date = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "fork_timing"

    def test_no_client_returns_neutral(self) -> None:
        """Test that no client returns neutral score with error."""
        user = make_mock_user()
        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 0
        assert "no_client" in result.breakdown
        assert "error" in result.details

    def test_no_prs_returns_neutral(self) -> None:
        """Test that user with no PRs gets neutral score."""
        user = make_mock_user()
        client = MagicMock()

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter([])
        client.get_user.return_value = mock_gh_user
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert result.details["total_prs"] == 0

    def test_many_instant_fork_prs_very_negative(self) -> None:
        """Test that many instant fork PRs get very negative score."""
        user = make_mock_user()
        client = MagicMock()

        # Create forks that were made just minutes before PRs
        fork_time = self.reference_date - timedelta(days=10, minutes=30)

        forks = [make_mock_fork(f"org/repo{i}", fork_time - timedelta(days=i)) for i in range(6)]

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter(forks)
        client.get_user.return_value = mock_gh_user

        # PRs created within 30 minutes of fork
        issues = [
            make_mock_issue(f"org/repo{i}", fork_time - timedelta(days=i) + timedelta(minutes=30))
            for i in range(6)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "many_instant_fork_prs" in result.breakdown
        very_quick = result.details["very_quick_fork_prs"]
        assert isinstance(very_quick, int) and very_quick >= 5

    def test_several_instant_fork_prs_negative(self) -> None:
        """Test that several instant fork PRs get negative score."""
        user = make_mock_user()
        client = MagicMock()

        fork_time = self.reference_date - timedelta(days=5)

        forks = [make_mock_fork(f"org/repo{i}", fork_time - timedelta(days=i)) for i in range(3)]

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter(forks)
        client.get_user.return_value = mock_gh_user

        # PRs created within 30 minutes of fork
        issues = [
            make_mock_issue(f"org/repo{i}", fork_time - timedelta(days=i) + timedelta(minutes=30))
            for i in range(3)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "several_instant_fork_prs" in result.breakdown

    def test_quick_fork_prs_negative(self) -> None:
        """Test that many quick (< 24h) fork PRs get negative score."""
        user = make_mock_user()
        client = MagicMock()

        base_time = self.reference_date - timedelta(days=30)

        # Create 10 forks
        forks = [
            make_mock_fork(f"org/repo{i}", base_time - timedelta(days=i * 2)) for i in range(10)
        ]

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter(forks)
        client.get_user.return_value = mock_gh_user

        # PRs created 12 hours after fork (quick but not instant)
        issues = [
            make_mock_issue(f"org/repo{i}", base_time - timedelta(days=i * 2) + timedelta(hours=12))
            for i in range(10)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "many_quick_fork_prs" in result.breakdown
        quick_prs = result.details["quick_fork_prs"]
        assert isinstance(quick_prs, int) and quick_prs >= 10

    def test_established_contributor_positive(self) -> None:
        """Test that established contributor with old forks gets positive score."""
        user = make_mock_user()
        client = MagicMock()

        # Forks created 30+ days before PRs
        fork_time = self.reference_date - timedelta(days=60)

        forks = [
            make_mock_fork(f"org/repo{i}", fork_time - timedelta(days=i * 5)) for i in range(6)
        ]

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter(forks)
        client.get_user.return_value = mock_gh_user

        # PRs created many days after fork
        issues = [
            make_mock_issue(f"org/repo{i}", fork_time - timedelta(days=i * 5) + timedelta(days=30))
            for i in range(6)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "established_contributor" in result.breakdown
        established = result.details["established_fork_prs"]
        assert isinstance(established, int) and established >= 5

    def test_mixed_fork_timing(self) -> None:
        """Test mixed fork timing patterns."""
        user = make_mock_user()
        client = MagicMock()

        base_time = self.reference_date - timedelta(days=30)

        # Mix of old and new forks
        forks = [
            make_mock_fork("org/old-repo1", base_time - timedelta(days=60)),
            make_mock_fork("org/old-repo2", base_time - timedelta(days=45)),
            make_mock_fork("org/new-repo1", base_time - timedelta(hours=10)),
        ]

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter(forks)
        client.get_user.return_value = mock_gh_user

        # PRs with varying fork age
        issues = [
            # PR 30 days after fork (established)
            make_mock_issue("org/old-repo1", base_time - timedelta(days=30)),
            # PR 20 days after fork (established)
            make_mock_issue("org/old-repo2", base_time - timedelta(days=25)),
            # PR 5 hours after fork (quick)
            make_mock_issue("org/new-repo1", base_time - timedelta(hours=5)),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        established = result.details["established_fork_prs"]
        assert isinstance(established, int) and established >= 2
        quick = result.details["quick_fork_prs"]
        assert isinstance(quick, int) and quick >= 1

    def test_prs_without_fork_data_neutral(self) -> None:
        """Test that PRs to repos user didn't fork are handled."""
        user = make_mock_user()
        client = MagicMock()

        # User has no forks
        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter([make_mock_non_fork()])
        client.get_user.return_value = mock_gh_user

        # But has PRs
        issues = [
            make_mock_issue("org/repo1", self.reference_date - timedelta(days=5)),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.details["prs_with_fork_data"] == 0
        assert result.details["total_prs"] == 1

    def test_api_error_returns_neutral(self) -> None:
        """Test that API errors return neutral score."""
        user = make_mock_user()
        client = MagicMock()
        client.get_user.side_effect = Exception("API error")

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert "api_error" in result.breakdown

    def test_details_include_all_metrics(self) -> None:
        """Test that details include all expected metrics."""
        user = make_mock_user()
        client = MagicMock()

        mock_gh_user = MagicMock()
        mock_gh_user.get_repos.return_value = iter([])
        client.get_user.return_value = mock_gh_user
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "total_prs" in result.details
        assert "prs_with_fork_data" in result.details
        assert "very_quick_fork_prs" in result.details
        assert "quick_fork_prs" in result.details
        assert "established_fork_prs" in result.details
        assert "avg_fork_to_pr_hours" in result.details
