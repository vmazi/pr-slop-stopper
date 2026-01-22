"""Tests for activity patterns heuristic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.heuristics.activity_patterns import ActivityPatternsHeuristic


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.login = login
    return user


def make_mock_pr(created_at: datetime) -> MagicMock:
    """Create a mock PR with creation date."""
    pr = MagicMock()
    pr.created_at = created_at
    return pr


class TestActivityPatternsHeuristic:
    """Tests for ActivityPatternsHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = ActivityPatternsHeuristic()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "activity_patterns"

    def test_no_client_returns_neutral(self) -> None:
        """Test that no client returns neutral score with error."""
        user = make_mock_user()
        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 0
        assert "no_client" in result.breakdown
        assert "error" in result.details

    def test_no_activity_returns_neutral(self) -> None:
        """Test that user with no activity gets neutral score."""
        user = make_mock_user()
        client = MagicMock()
        client.search_issues.return_value = iter([])

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score == 0
        assert result.details["total_prs"] == 0

    def test_consistent_contributor_positive_score(self) -> None:
        """Test that consistent contributor gets positive score."""
        user = make_mock_user()
        client = MagicMock()

        # Create PRs spread across 8 months at reasonable hours (not midnight)
        prs = []
        for month_offset in range(8):
            month_date = self.reference_date - relativedelta(months=month_offset)
            # 2 PRs per month = 16 total, at 10am and 2pm
            for day_offset, hour in [(0, 10), (5, 14)]:
                pr_date = (month_date - timedelta(days=day_offset)).replace(hour=hour)
                prs.append(make_mock_pr(pr_date))

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score > 0
        assert "consistent_contributor" in result.breakdown
        assert result.details["consistent_activity"] is True

    def test_regular_contributor_moderate_positive(self) -> None:
        """Test that regular contributor gets moderate positive score."""
        user = make_mock_user()
        client = MagicMock()

        # Create PRs spread across 4 months (6 total)
        prs = []
        for month_offset in range(4):
            month_date = self.reference_date - relativedelta(months=month_offset)
            prs.append(make_mock_pr(month_date))
            if month_offset < 2:
                prs.append(make_mock_pr(month_date - timedelta(days=5)))

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score >= 0
        active_months = result.details["active_months"]
        assert isinstance(active_months, int) and active_months >= 3

    def test_burst_activity_negative_score(self) -> None:
        """Test that burst activity concentrated in one month gets negative score."""
        user = make_mock_user()
        client = MagicMock()

        # Create 10 PRs in one month, 2 in another (burst pattern)
        burst_month = self.reference_date - relativedelta(months=1)
        other_month = self.reference_date - relativedelta(months=3)

        prs = [
            make_mock_pr(burst_month.replace(hour=10) - timedelta(days=i)) for i in range(10)
        ] + [make_mock_pr(other_month.replace(hour=10) - timedelta(days=i)) for i in range(2)]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "burst_activity" in result.breakdown
        assert result.details["burst_detected"] is True

    def test_burst_two_months_moderate_negative(self) -> None:
        """Test that burst activity in two months gets moderate negative."""
        user = make_mock_user()
        client = MagicMock()

        # Create 15 PRs in 2 months (burst pattern)
        prs = []
        for month_offset in range(2):
            month_date = self.reference_date - relativedelta(months=month_offset + 1)
            for day in range(7 if month_offset == 0 else 8):
                prs.append(make_mock_pr(month_date - timedelta(days=day)))

        # Add 1 PR in a third month to have some spread
        prs.append(make_mock_pr(self.reference_date - relativedelta(months=5)))

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert result.details["burst_detected"] is True

    def test_suspicious_night_timing_negative(self) -> None:
        """Test that suspicious night activity timing gets negative score."""
        user = make_mock_user()
        client = MagicMock()

        # Create 12 PRs all at 3am (suspicious timing)
        prs = []
        for month_offset in range(4):
            month_date = self.reference_date - relativedelta(months=month_offset)
            for _ in range(3):
                # Create at 3am
                pr_date = month_date.replace(hour=3, minute=0)
                prs.append(make_mock_pr(pr_date))

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "suspicious_timing" in result.breakdown
        night_ratio = result.details["night_ratio"]
        assert isinstance(night_ratio, (int, float)) and night_ratio >= 80

    def test_dormancy_spike_negative(self) -> None:
        """Test that dormancy followed by spike gets negative score."""
        user = make_mock_user()
        client = MagicMock()

        # Create 2 old PRs, then gap, then 10 recent PRs
        old_date = self.reference_date - relativedelta(months=10)
        prs = [
            make_mock_pr(old_date),
            make_mock_pr(old_date - timedelta(days=5)),
        ]

        # Recent burst after 9 month gap
        for i in range(10):
            prs.append(make_mock_pr(self.reference_date - timedelta(days=i)))

        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert result.score < 0
        assert "dormancy_spike" in result.breakdown

    def test_weekend_ratio_tracked(self) -> None:
        """Test that weekend activity ratio is tracked."""
        user = make_mock_user()
        client = MagicMock()

        # Create PRs on Saturday (June 15, 2024 was a Saturday)
        saturday = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
        prs = [make_mock_pr(saturday - timedelta(weeks=i)) for i in range(5)]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "weekend_ratio" in result.details

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

        prs = [make_mock_pr(self.reference_date - relativedelta(months=i)) for i in range(3)]
        client.search_issues.return_value = iter(prs)

        result = self.heuristic.evaluate(
            user, reference_date=self.reference_date, github_client=client
        )

        assert "total_prs" in result.details
        assert "active_months" in result.details
        assert "burst_detected" in result.details
        assert "consistent_activity" in result.details
        assert "weekend_ratio" in result.details
        assert "night_ratio" in result.details

    def test_detect_burst_pattern_helper(self) -> None:
        """Test the burst pattern detection helper method."""
        # Single month dominance
        monthly = {"2024-01": 8, "2024-02": 2}
        result = self.heuristic._detect_burst_pattern(monthly, 10)
        assert result < 0

        # Two month dominance
        monthly = {"2024-01": 5, "2024-02": 4, "2024-03": 1}
        result = self.heuristic._detect_burst_pattern(monthly, 10)
        assert result < 0

        # Spread activity (no burst)
        monthly = {"2024-01": 3, "2024-02": 3, "2024-03": 2, "2024-04": 2}
        result = self.heuristic._detect_burst_pattern(monthly, 10)
        assert result == 0
