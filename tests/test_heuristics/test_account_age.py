"""Tests for account age heuristic."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.heuristics.account_age import AccountAgeHeuristic


def make_mock_user(created_at: datetime) -> MagicMock:
    """Create a mock user with specified creation date."""
    user = MagicMock()
    user.created_at = created_at
    return user


class TestAccountAgeHeuristic:
    """Tests for AccountAgeHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = AccountAgeHeuristic()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "account_age"

    def test_very_new_account(self) -> None:
        """Test account less than 1 month old."""
        created = self.reference_date - relativedelta(days=15)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == -20
        assert result.details["tier"] == "very_new"

    def test_new_account(self) -> None:
        """Test account 1-3 months old."""
        created = self.reference_date - relativedelta(months=2)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == -15
        assert result.details["tier"] == "new"

    def test_recent_account(self) -> None:
        """Test account 3-6 months old."""
        created = self.reference_date - relativedelta(months=4)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == -10
        assert result.details["tier"] == "recent"

    def test_neutral_account(self) -> None:
        """Test account 6 months to 1 year old."""
        created = self.reference_date - relativedelta(months=8)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 0
        assert result.details["tier"] == "neutral"

    def test_established_account(self) -> None:
        """Test account 1-3 years old."""
        created = self.reference_date - relativedelta(years=2)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 5
        assert result.details["tier"] == "established"

    def test_mature_account(self) -> None:
        """Test account 3-5 years old."""
        created = self.reference_date - relativedelta(years=4)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 10
        assert result.details["tier"] == "mature"

    def test_veteran_account(self) -> None:
        """Test account 5+ years old."""
        created = self.reference_date - relativedelta(years=6)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 15
        assert result.details["tier"] == "veteran"

    def test_boundary_exactly_one_month(self) -> None:
        """Test boundary at exactly 1 month (30 days)."""
        created = self.reference_date - relativedelta(days=30)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        # 30 days should be in "new" tier, not "very_new"
        assert result.score == -15
        assert result.details["tier"] == "new"

    def test_boundary_exactly_five_years(self) -> None:
        """Test boundary at exactly 5 years."""
        created = self.reference_date - relativedelta(years=5)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert result.score == 15
        assert result.details["tier"] == "veteran"

    def test_naive_datetime_handling(self) -> None:
        """Test that naive datetime is handled correctly."""
        # Create naive datetime (no timezone)
        created = datetime(2020, 1, 1)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        # Should not raise an error
        assert result.score > 0  # Account is old

    def test_details_contain_age_info(self) -> None:
        """Test that details contain age information."""
        created = self.reference_date - relativedelta(years=2, months=6)
        user = make_mock_user(created)

        result = self.heuristic.evaluate(user, reference_date=self.reference_date)

        assert "account_age_days" in result.details
        assert "account_age_months" in result.details
        assert "account_age_years" in result.details
        assert "created_at" in result.details
        age_months = result.details["account_age_months"]
        assert isinstance(age_months, int) and age_months >= 30  # About 2.5 years
