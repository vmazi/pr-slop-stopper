"""Tests for contribution type patterns heuristic."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pr_slop_stopper.core.heuristics.contribution_type import ContributionTypeHeuristic


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.login = login
    return user


def make_mock_file(filename: str, changes: int = 10) -> MagicMock:
    """Create a mock PR file."""
    file = MagicMock()
    file.filename = filename
    file.changes = changes
    return file


def make_mock_pr_with_files(files: list[MagicMock]) -> MagicMock:
    """Create a mock PR with files."""
    pr = MagicMock()
    pr.get_files.return_value = files
    return pr


def make_mock_issue(
    number: int,
    repo_name: str,
    pr_files: list[MagicMock],
) -> MagicMock:
    """Create a mock issue with repository and PR."""
    issue = MagicMock()
    issue.number = number

    repo = MagicMock()
    repo.full_name = repo_name
    repo.get_pull.return_value = make_mock_pr_with_files(pr_files)
    issue.repository = repo

    return issue


class TestContributionTypeHeuristic:
    """Tests for ContributionTypeHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = ContributionTypeHeuristic()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "contribution_type"

    def test_no_client_returns_neutral(self) -> None:
        """Test that no client returns neutral score with error."""
        user = make_mock_user()
        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 0
        assert "no_client" in result.breakdown
        assert "error" in result.details

    def test_no_contributions_returns_neutral(self) -> None:
        """Test that user with no contributions gets neutral score."""
        user = make_mock_user()
        client = MagicMock()
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert result.details["total_prs"] == 0

    def test_strong_code_contributor_positive_score(self) -> None:
        """Test that strong code contributor gets positive score."""
        user = make_mock_user()
        client = MagicMock()

        # 6 code PRs out of 7 total (86% code ratio)
        issues = [
            make_mock_issue(i, "org/repo", [make_mock_file("src/main.py", 50)]) for i in range(6)
        ] + [make_mock_issue(6, "org/repo", [make_mock_file("README.md", 10)])]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert (
            "strong_code_contributor" in result.breakdown or "code_contributor" in result.breakdown
        )

    def test_mixed_contributions_positive(self) -> None:
        """Test that mixed contributions (code + docs) get positive score."""
        user = make_mock_user()
        client = MagicMock()

        # 4 mixed PRs (code + docs together)
        issues = [
            make_mock_issue(
                i, "org/repo", [make_mock_file("src/main.py", 50), make_mock_file("README.md", 10)]
            )
            for i in range(4)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "mixed_contributions" in result.breakdown

    def test_doc_only_spam_pattern_negative(self) -> None:
        """Test that docs-only high volume gets negative score."""
        user = make_mock_user()
        client = MagicMock()

        # 12 doc-only PRs (100% doc ratio)
        issues = [
            make_mock_issue(i, f"org/repo{i}", [make_mock_file("README.md", 10)]) for i in range(12)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "doc_only_spam_pattern" in result.breakdown

    def test_doc_heavy_pattern_moderate_negative(self) -> None:
        """Test that doc-heavy pattern gets moderate negative score."""
        user = make_mock_user()
        client = MagicMock()

        # 5 doc PRs, 0 code PRs (100% doc ratio, but lower volume)
        issues = [
            make_mock_issue(i, f"org/repo{i}", [make_mock_file("CHANGELOG.md", 10)])
            for i in range(5)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "doc_heavy_pattern" in result.breakdown

    def test_trivial_spam_pattern_negative(self) -> None:
        """Test that many trivial PRs get negative score."""
        user = make_mock_user()
        client = MagicMock()

        # 6 trivial PRs (small changes, few files)
        issues = [
            make_mock_issue(i, f"org/repo{i}", [make_mock_file("README.md", 2)]) for i in range(6)
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        # Should trigger both doc pattern and trivial pattern
        trivial_prs = result.details.get("trivial_prs", 0)
        assert isinstance(trivial_prs, int) and trivial_prs >= 5

    def test_file_classification_code(self) -> None:
        """Test that code files are classified correctly."""
        files = [make_mock_file("src/main.py"), make_mock_file("lib/utils.js")]
        result = self.heuristic._classify_pr(files)
        assert result == "code"

    def test_file_classification_doc(self) -> None:
        """Test that doc files are classified correctly."""
        files = [make_mock_file("README.md"), make_mock_file("docs/guide.rst")]
        result = self.heuristic._classify_pr(files)
        assert result == "doc"

    def test_file_classification_config(self) -> None:
        """Test that config files are classified correctly."""
        files = [make_mock_file("config.yaml"), make_mock_file("settings.json")]
        result = self.heuristic._classify_pr(files)
        assert result == "config"

    def test_file_classification_mixed(self) -> None:
        """Test that mixed files are classified correctly."""
        files = [make_mock_file("src/main.py"), make_mock_file("README.md")]
        result = self.heuristic._classify_pr(files)
        assert result == "mixed"

    def test_trivial_pr_detection(self) -> None:
        """Test that trivial PRs are detected correctly."""
        # Trivial: 1 file with 5 changes
        trivial_files = [make_mock_file("README.md", 5)]
        assert self.heuristic._is_trivial_pr(trivial_files) is True

        # Not trivial: 1 file with 50 changes
        large_files = [make_mock_file("src/main.py", 50)]
        assert self.heuristic._is_trivial_pr(large_files) is False

        # Not trivial: 5 files
        many_files = [make_mock_file(f"file{i}.py", 2) for i in range(5)]
        assert self.heuristic._is_trivial_pr(many_files) is False

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
            make_mock_issue(0, "org/repo", [make_mock_file("src/main.py", 50)]),
            make_mock_issue(1, "org/repo", [make_mock_file("README.md", 10)]),
        ]
        client.search_issues.return_value = iter(issues)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "total_prs" in result.details
        assert "code_prs" in result.details
        assert "doc_prs" in result.details
        assert "config_prs" in result.details
        assert "mixed_prs" in result.details
        assert "trivial_prs" in result.details
