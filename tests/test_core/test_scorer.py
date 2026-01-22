"""Tests for reputation scorer."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.scorer import ReputationScorer, ScoringResult


def make_mock_user(
    *,
    created_at: datetime | None = None,
    followers: int = 0,
    following: int = 0,
    avatar_url: str | None = None,
    bio: str | None = None,
    company: str | None = None,
    location: str | None = None,
    blog: str | None = None,
    twitter_username: str | None = None,
    name: str | None = None,
    email: str | None = None,
) -> MagicMock:
    """Create a mock user with specified attributes."""
    user = MagicMock()
    user.created_at = created_at or datetime(2020, 1, 1, tzinfo=UTC)
    user.followers = followers
    user.following = following
    user.avatar_url = avatar_url
    user.bio = bio
    user.company = company
    user.location = location
    user.blog = blog
    user.twitter_username = twitter_username
    user.name = name
    user.email = email
    return user


class TestScoringResult:
    """Tests for ScoringResult dataclass."""

    def test_allow_recommendation(self) -> None:
        """Test allow recommendation for positive score."""
        result = ScoringResult(total_score=10, clamped_score=10, breakdown={})
        assert result.recommendation == "allow"

    def test_warn_recommendation(self) -> None:
        """Test warn recommendation for score at warning threshold."""
        result = ScoringResult(total_score=-15, clamped_score=-15, breakdown={})
        assert result.recommendation == "warn"

    def test_close_recommendation(self) -> None:
        """Test close recommendation for score at close threshold."""
        result = ScoringResult(total_score=-30, clamped_score=-30, breakdown={})
        assert result.recommendation == "close"


class TestReputationScorer:
    """Tests for ReputationScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = ReputationScorer()
        self.reference_date = datetime(2024, 6, 15, tzinfo=UTC)

    def test_good_user_positive_score(self) -> None:
        """Test user with good signals gets positive score."""
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(years=5),
            followers=100,
            following=50,
            avatar_url="https://example.com/avatar.png",
            bio="Experienced developer",
            company="Tech Corp",
            location="San Francisco",
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        assert result.total_score > 0
        assert result.recommendation == "allow"
        assert "account_age" in result.breakdown
        assert "follower_patterns" in result.breakdown
        assert "profile_completeness" in result.breakdown

    def test_suspicious_user_negative_score(self) -> None:
        """Test user with suspicious signals gets negative score."""
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(days=10),  # Very new
            followers=2,
            following=500,  # Follow spam pattern
            # Empty profile
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        assert result.total_score < 0
        assert result.recommendation in ("warn", "close")

    def test_score_clamping_max(self) -> None:
        """Test score is clamped to max."""
        # Create an extremely good user
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(years=10),
            followers=10000,
            avatar_url="https://example.com/avatar.png",
            bio="Legendary developer",
            company="Big Tech",
            location="Everywhere",
            blog="https://linkedin.com/in/legendarydev",
            twitter_username="legendary",
            name="Legendary Dev",
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        assert result.clamped_score <= 100

    def test_score_clamping_min(self) -> None:
        """Test score is clamped to min."""
        # Create an extremely suspicious user
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(days=1),  # Brand new
            followers=0,
            following=1000,  # Major follow spam
            # Empty profile
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        assert result.clamped_score >= -100

    def test_custom_thresholds(self) -> None:
        """Test custom warning and close thresholds."""
        scorer = ReputationScorer(warning_threshold=-5, close_threshold=-15)

        user = make_mock_user(
            created_at=self.reference_date - relativedelta(months=4),  # -10 score
        )

        result = scorer.calculate_score(user, reference_date=self.reference_date)

        # With threshold at -5, a -10 score should warn
        # But profile and follower penalties also apply
        assert result.total_score < -5

    def test_enabled_heuristics_filter(self) -> None:
        """Test that only enabled heuristics are evaluated."""
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(years=5),
            followers=100,
        )

        result = self.scorer.calculate_score(
            user,
            enabled_heuristics=["account_age"],
            reference_date=self.reference_date,
        )

        assert "account_age" in result.breakdown
        assert "follower_patterns" not in result.breakdown
        assert "profile_completeness" not in result.breakdown
        assert len(result.heuristic_results) == 1

    def test_heuristic_results_included(self) -> None:
        """Test that individual heuristic results are included."""
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(years=2),
            followers=25,
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        # We have 8 heuristics now (original 3 + 5 new complex ones)
        assert len(result.heuristic_results) == 8
        names = [r.name for r in result.heuristic_results]
        # Original heuristics
        assert "account_age" in names
        assert "follower_patterns" in names
        assert "profile_completeness" in names
        # New complex heuristics
        assert "pr_acceptance_rate" in names
        assert "contribution_type" in names
        assert "activity_patterns" in names
        assert "notable_contributions" in names
        assert "fork_timing" in names

    def test_total_score_is_sum(self) -> None:
        """Test that total score is sum of all heuristic scores."""
        user = make_mock_user(
            created_at=self.reference_date - relativedelta(years=2),
            followers=25,
        )

        result = self.scorer.calculate_score(user, reference_date=self.reference_date)

        expected_total = sum(r.score for r in result.heuristic_results)
        assert result.total_score == expected_total
