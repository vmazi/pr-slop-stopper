"""Tests for PR acceptance rate heuristic."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.heuristics.pr_acceptance_rate import PRAcceptanceRateHeuristic


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.login = login
    return user


def make_mock_pr(
    *,
    number: int = 1,
    state: str = "closed",
    merged: bool = True,
    created_at: datetime | None = None,
    repository: str = "owner/repo",
) -> MagicMock:
    """Create a mock PR search result."""
    pr = MagicMock()
    pr.number = number
    pr.state = state
    pr.created_at = created_at or datetime.now(UTC)
    pr.repository = MagicMock()
    pr.repository.full_name = repository

    # Mock pull_request attribute for merged status
    if merged and state == "closed":
        pr.pull_request = {"merged_at": "2024-01-01T00:00:00Z"}
    else:
        pr.pull_request = {"merged_at": None}

    return pr


class TestPRAcceptanceRateHeuristic:
    """Tests for PRAcceptanceRateHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = PRAcceptanceRateHeuristic()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "pr_acceptance_rate"

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
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert result.details["total_prs"] == 0

    def test_high_merge_rate_positive_score(self) -> None:
        """Test that high merge rate gives positive score."""
        user = make_mock_user()
        client = MagicMock()

        # 8 merged, 2 closed = 80% merge rate
        prs = [make_mock_pr(number=i, state="closed", merged=True) for i in range(8)] + [
            make_mock_pr(number=i + 8, state="closed", merged=False) for i in range(2)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "high_merge_rate" in result.breakdown or "good_merge_rate" in result.breakdown

    def test_good_merge_rate_moderate_score(self) -> None:
        """Test that good merge rate gives moderate positive score."""
        user = make_mock_user()
        client = MagicMock()

        # 6 merged, 4 closed = 60% merge rate
        prs = [make_mock_pr(number=i, state="closed", merged=True) for i in range(6)] + [
            make_mock_pr(number=i + 6, state="closed", merged=False) for i in range(4)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score >= 0

    def test_low_merge_high_volume_negative(self) -> None:
        """Test that low merge rate with high volume gives negative score."""
        user = make_mock_user()
        client = MagicMock()

        # 4 merged, 21 closed = ~16% merge rate, 25 total
        prs = [make_mock_pr(number=i, state="closed", merged=True) for i in range(4)] + [
            make_mock_pr(number=i + 4, state="closed", merged=False) for i in range(21)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "low_merge_high_volume" in result.breakdown

    def test_spam_month_detection(self) -> None:
        """Test detection of spam months (>10 PRs with <20% merge)."""
        user = make_mock_user()
        client = MagicMock()

        # Create 15 PRs in same month with only 2 merged (<20%)
        month_date = self.reference_date - relativedelta(months=2)
        prs = [
            make_mock_pr(number=i, state="closed", merged=True, created_at=month_date)
            for i in range(2)
        ] + [
            make_mock_pr(number=i + 2, state="closed", merged=False, created_at=month_date)
            for i in range(13)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        spam_months = result.details["spam_months"]
        assert isinstance(spam_months, int) and spam_months >= 1
        assert result.score < 0

    def test_multiple_spam_months_severe_penalty(self) -> None:
        """Test that multiple spam months get severe penalty."""
        user = make_mock_user()
        client = MagicMock()

        # Create spam PRs in 3 different months
        prs = []
        for month_offset in range(3):
            month_date = self.reference_date - relativedelta(months=month_offset + 1)
            # 2 merged, 12 closed = 14% merge rate per month
            prs.extend(
                [
                    make_mock_pr(
                        number=month_offset * 14 + i,
                        state="closed",
                        merged=True,
                        created_at=month_date,
                    )
                    for i in range(2)
                ]
            )
            prs.extend(
                [
                    make_mock_pr(
                        number=month_offset * 14 + i + 2,
                        state="closed",
                        merged=False,
                        created_at=month_date,
                    )
                    for i in range(12)
                ]
            )

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        spam_months = result.details["spam_months"]
        assert isinstance(spam_months, int) and spam_months >= 3
        assert "multiple_spam_months" in result.breakdown
        assert result.score <= -25

    def test_spray_pattern_detection(self) -> None:
        """Test detection of spray pattern (many repos, low merge rate)."""
        user = make_mock_user()
        client = MagicMock()

        # 25 PRs to 25 different repos with 20% merge rate
        prs = [
            make_mock_pr(number=i, state="closed", merged=True, repository=f"org/repo{i}")
            for i in range(5)
        ] + [
            make_mock_pr(number=i + 5, state="closed", merged=False, repository=f"org/repo{i + 5}")
            for i in range(20)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        unique_repos = result.details["unique_repos"]
        assert isinstance(unique_repos, int) and unique_repos >= 20
        assert result.score < 0

    def test_open_prs_not_counted_in_merge_rate(self) -> None:
        """Test that open PRs don't affect merge rate calculation."""
        user = make_mock_user()
        client = MagicMock()

        # 5 merged, 5 open = 100% merge rate (open not counted)
        prs = [make_mock_pr(number=i, state="closed", merged=True) for i in range(5)] + [
            make_mock_pr(number=i + 5, state="open", merged=False) for i in range(5)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.details["merged_prs"] == 5
        assert result.details["open_prs"] == 5
        # With only merged PRs counted, merge rate should be 100%
        assert result.details["merge_rate"] == 100.0

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

        prs = [
            make_mock_pr(number=i, state="closed", merged=True, repository="org/repo1")
            for i in range(3)
        ] + [
            make_mock_pr(number=i + 3, state="closed", merged=False, repository="org/repo2")
            for i in range(2)
        ]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "total_prs" in result.details
        assert "merged_prs" in result.details
        assert "closed_prs" in result.details
        assert "open_prs" in result.details
        assert "merge_rate" in result.details
        assert "spam_months" in result.details
        assert "unique_repos" in result.details
