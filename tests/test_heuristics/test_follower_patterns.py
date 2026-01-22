"""Tests for follower patterns heuristic."""

from unittest.mock import MagicMock

from pr_slop_stopper.core.heuristics.follower_patterns import FollowerPatternsHeuristic


def make_mock_user(followers: int, following: int) -> MagicMock:
    """Create a mock user with specified follower counts."""
    user = MagicMock()
    user.followers = followers
    user.following = following
    return user


class TestFollowerPatternsHeuristic:
    """Tests for FollowerPatternsHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = FollowerPatternsHeuristic()

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "follower_patterns"

    def test_popular_tier(self) -> None:
        """Test user with 50+ followers."""
        user = make_mock_user(followers=100, following=50)

        result = self.heuristic.evaluate(user)

        assert result.score == 8
        assert result.details["tier"] == "popular"
        assert "high_followers" in result.breakdown

    def test_recognized_tier(self) -> None:
        """Test user with 20-49 followers."""
        user = make_mock_user(followers=30, following=100)

        result = self.heuristic.evaluate(user)

        assert result.score == 5
        assert result.details["tier"] == "recognized"
        assert "moderate_followers" in result.breakdown

    def test_basic_tier(self) -> None:
        """Test user with 5-19 followers."""
        user = make_mock_user(followers=8, following=20)

        result = self.heuristic.evaluate(user)

        assert result.score == 2
        assert result.details["tier"] == "basic"
        assert "some_followers" in result.breakdown

    def test_minimal_tier(self) -> None:
        """Test user with <5 followers."""
        user = make_mock_user(followers=2, following=10)

        result = self.heuristic.evaluate(user)

        assert result.score == 0
        assert result.details["tier"] == "minimal"

    def test_follow_spam_extreme(self) -> None:
        """Test extreme follow spam pattern (500+ following, <10 followers)."""
        user = make_mock_user(followers=5, following=1000)

        result = self.heuristic.evaluate(user)

        # +2 (5 followers, basic tier) -10 (follow spam) = -8
        assert result.score == -8
        assert "follow_spam_extreme" in result.breakdown

    def test_high_follow_ratio(self) -> None:
        """Test high following/follower ratio (>50:1)."""
        user = make_mock_user(followers=10, following=600)

        result = self.heuristic.evaluate(user)

        # +2 (10 followers, basic tier) -8 (high ratio) = -6
        assert result.score == -6
        assert "high_follow_ratio" in result.breakdown

    def test_new_user_no_penalty(self) -> None:
        """Test new user with 0 followers isn't penalized."""
        user = make_mock_user(followers=0, following=5)

        result = self.heuristic.evaluate(user)

        assert result.score == 0
        assert result.details["tier"] == "minimal"
        assert "follow_spam_extreme" not in result.breakdown
        assert "high_follow_ratio" not in result.breakdown

    def test_normal_active_user(self) -> None:
        """Test normal user with good follower ratio."""
        user = make_mock_user(followers=100, following=200)

        result = self.heuristic.evaluate(user)

        assert result.score == 8  # Popular tier, no penalties
        assert "follow_spam_extreme" not in result.breakdown
        assert "high_follow_ratio" not in result.breakdown

    def test_ratio_calculation_zero_followers(self) -> None:
        """Test ratio is None when followers is 0 and following > 0."""
        user = make_mock_user(followers=0, following=100)

        result = self.heuristic.evaluate(user)

        assert result.details["ratio"] is None

    def test_ratio_calculation_normal(self) -> None:
        """Test ratio is calculated correctly."""
        user = make_mock_user(followers=50, following=100)

        result = self.heuristic.evaluate(user)

        assert result.details["ratio"] == 2.0

    def test_high_ratio_requires_significant_following(self) -> None:
        """Test high ratio penalty requires >100 following."""
        user = make_mock_user(followers=1, following=60)

        result = self.heuristic.evaluate(user)

        # Ratio is 60:1 but following is only 60, so no penalty
        assert "high_follow_ratio" not in result.breakdown
