"""Tests for profile completeness heuristic."""

from unittest.mock import MagicMock

from pr_slop_stopper.core.heuristics.profile_completeness import (
    ProfileCompletenessHeuristic,
    extract_linkedin_url,
    is_default_avatar,
    name_matches_linkedin,
)


def make_mock_user(
    avatar_url: str | None = None,
    bio: str | None = None,
    company: str | None = None,
    location: str | None = None,
    blog: str | None = None,
    twitter_username: str | None = None,
    name: str | None = None,
    email: str | None = None,
) -> MagicMock:
    """Create a mock user with specified profile fields."""
    user = MagicMock()
    user.avatar_url = avatar_url
    user.bio = bio
    user.company = company
    user.location = location
    user.blog = blog
    user.twitter_username = twitter_username
    user.name = name
    user.email = email
    return user


class TestIsDefaultAvatar:
    """Tests for is_default_avatar function."""

    def test_none_avatar(self) -> None:
        """Test None avatar is default."""
        assert is_default_avatar(None) is True

    def test_empty_avatar(self) -> None:
        """Test empty string avatar is default."""
        assert is_default_avatar("") is True

    def test_identicon_avatar(self) -> None:
        """Test identicon URL is detected as default."""
        url = "https://avatars.githubusercontent.com/u/12345?identicon"
        assert is_default_avatar(url) is True

    def test_custom_avatar(self) -> None:
        """Test custom avatar URL is not default."""
        url = "https://avatars.githubusercontent.com/u/12345?v=4"
        assert is_default_avatar(url) is False


class TestExtractLinkedinUrl:
    """Tests for extract_linkedin_url function."""

    def test_no_blog(self) -> None:
        """Test None blog returns None."""
        assert extract_linkedin_url(None) is None

    def test_no_linkedin(self) -> None:
        """Test blog without LinkedIn returns None."""
        assert extract_linkedin_url("https://example.com") is None

    def test_linkedin_url(self) -> None:
        """Test LinkedIn URL is extracted."""
        url = extract_linkedin_url("https://linkedin.com/in/johndoe")
        assert url == "linkedin.com/in/johndoe"

    def test_linkedin_mixed_case(self) -> None:
        """Test LinkedIn URL extraction is case-insensitive."""
        url = extract_linkedin_url("https://LinkedIn.com/in/JohnDoe")
        assert url == "linkedin.com/in/johndoe"


class TestNameMatchesLinkedin:
    """Tests for name_matches_linkedin function."""

    def test_no_name(self) -> None:
        """Test None name returns False."""
        assert name_matches_linkedin(None, "linkedin.com/in/johndoe") is False

    def test_no_linkedin(self) -> None:
        """Test None LinkedIn returns False."""
        assert name_matches_linkedin("John Doe", None) is False

    def test_matching_name(self) -> None:
        """Test matching first and last name."""
        assert name_matches_linkedin("John Doe", "linkedin.com/in/johndoe") is True

    def test_matching_with_hyphen(self) -> None:
        """Test matching with hyphenated slug."""
        assert name_matches_linkedin("John Doe", "linkedin.com/in/john-doe") is True

    def test_single_name(self) -> None:
        """Test single name matching."""
        assert name_matches_linkedin("Johndoe", "linkedin.com/in/johndoe") is True

    def test_non_matching_name(self) -> None:
        """Test non-matching name."""
        assert name_matches_linkedin("Jane Smith", "linkedin.com/in/johndoe") is False


class TestProfileCompletenessHeuristic:
    """Tests for ProfileCompletenessHeuristic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.heuristic = ProfileCompletenessHeuristic()

    def test_name(self) -> None:
        """Test heuristic name."""
        assert self.heuristic.name == "profile_completeness"

    def test_complete_profile(self) -> None:
        """Test fully complete profile gets max positive score."""
        user = make_mock_user(
            avatar_url="https://avatars.githubusercontent.com/u/123?v=4",
            bio="Software engineer",
            company="@acme-corp",
            location="San Francisco",
            blog="https://linkedin.com/in/johndoe",
            twitter_username="johndoe",
            name="John Doe",
        )

        result = self.heuristic.evaluate(user)

        # +5 (avatar) +3 (bio) +3 (company) +2 (location) +3 (blog) +5 (linkedin) +2 (twitter) = 23
        assert result.score == 23
        assert result.details["has_avatar"] is True
        assert result.details["has_linkedin"] is True

    def test_empty_profile(self) -> None:
        """Test empty profile gets max negative score."""
        user = make_mock_user()

        result = self.heuristic.evaluate(user)

        # -5 (no avatar) -5 (empty profile penalty) = -10
        assert result.score == -10
        assert result.details["has_avatar"] is False
        assert "no_profile_picture" in result.breakdown
        assert "empty_profile_penalty" in result.breakdown

    def test_minimal_profile(self) -> None:
        """Test profile with just bio avoids empty penalty."""
        user = make_mock_user(bio="Just a developer")

        result = self.heuristic.evaluate(user)

        # -5 (no avatar) +3 (bio) = -2 (no empty penalty because has bio)
        assert result.score == -2
        assert result.details["has_bio"] is True
        assert "empty_profile_penalty" not in result.breakdown

    def test_profile_with_email_avoids_penalty(self) -> None:
        """Test profile with email but no bio avoids empty penalty."""
        user = make_mock_user(email="test@example.com")

        result = self.heuristic.evaluate(user)

        # -5 (no avatar) = -5 (no empty penalty because has email)
        assert result.score == -5
        assert "empty_profile_penalty" not in result.breakdown

    def test_identicon_avatar_penalty(self) -> None:
        """Test identicon avatar gets penalty."""
        user = make_mock_user(
            avatar_url="https://avatars.githubusercontent.com/u/123?identicon",
            bio="Developer",
        )

        result = self.heuristic.evaluate(user)

        # -5 (identicon avatar) +3 (bio) = -2
        assert result.score == -2
        assert result.details["has_avatar"] is False

    def test_linkedin_without_name_match(self) -> None:
        """Test LinkedIn URL without name match doesn't get bonus."""
        user = make_mock_user(
            blog="https://linkedin.com/in/johndoe",
            name="Jane Smith",
        )

        result = self.heuristic.evaluate(user)

        # Blog gives +3, but no LinkedIn match bonus
        assert result.details["has_blog"] is True
        assert result.details["has_linkedin"] is False
        assert "linkedin_match" not in result.breakdown
