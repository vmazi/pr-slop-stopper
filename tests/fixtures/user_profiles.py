"""Sample user profiles for testing."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta


def make_mock_user(
    *,
    login: str = "test-user",
    created_at: datetime | None = None,
    avatar_url: str | None = "https://avatars.githubusercontent.com/u/123456",
    bio: str | None = "Software developer",
    company: str | None = "Acme Corp",
    location: str | None = "San Francisco, CA",
    blog: str | None = "https://example.com",
    twitter_username: str | None = "testuser",
    name: str | None = "Test User",
    email: str | None = "test@example.com",
    followers: int = 50,
    following: int = 30,
) -> MagicMock:
    """Create a mock GitHub user with specified attributes.

    Args:
        login: GitHub username
        created_at: Account creation date (default: 3 years ago)
        avatar_url: Profile picture URL
        bio: User biography
        company: Company name
        location: Location string
        blog: Blog/website URL
        twitter_username: Twitter handle
        name: Display name
        email: Public email
        followers: Follower count
        following: Following count

    Returns:
        MagicMock configured as a GitHub user
    """
    if created_at is None:
        created_at = datetime.now(UTC) - relativedelta(years=3)

    user = MagicMock()
    user.login = login
    user.created_at = created_at
    user.avatar_url = avatar_url
    user.bio = bio
    user.company = company
    user.location = location
    user.blog = blog
    user.twitter_username = twitter_username
    user.name = name
    user.email = email
    user.followers = followers
    user.following = following
    return user


def make_good_user() -> MagicMock:
    """Create a mock user with a good reputation profile.

    This represents a well-established, trustworthy contributor.

    Returns:
        MagicMock configured as a reputable GitHub user
    """
    return make_mock_user(
        login="good-contributor",
        created_at=datetime.now(UTC) - relativedelta(years=5),
        avatar_url="https://avatars.githubusercontent.com/u/100",
        bio="Open source enthusiast and full-stack developer",
        company="@big-tech-company",
        location="Seattle, WA",
        blog="https://linkedin.com/in/good-contributor",
        twitter_username="goodcontributor",
        name="Good Contributor",
        email="good@example.com",
        followers=200,
        following=50,
    )


def make_suspicious_user() -> MagicMock:
    """Create a mock user with a suspicious profile.

    This represents a user who might be a spammer.

    Returns:
        MagicMock configured as a suspicious GitHub user
    """
    return make_mock_user(
        login="suspicious-user",
        created_at=datetime.now(UTC) - relativedelta(months=2),
        avatar_url=None,  # No avatar
        bio=None,  # No bio
        company=None,
        location=None,
        blog=None,
        twitter_username=None,
        name=None,
        email=None,
        followers=2,
        following=500,  # Follow spam pattern
    )


def make_spam_user() -> MagicMock:
    """Create a mock user with a very spammy profile.

    This represents a clear spam account.

    Returns:
        MagicMock configured as a spam GitHub user
    """
    return make_mock_user(
        login="spam-account",
        created_at=datetime.now(UTC) - relativedelta(days=7),  # Very new
        avatar_url="https://avatars.githubusercontent.com/identicon/123",  # Default
        bio=None,
        company=None,
        location=None,
        blog=None,
        twitter_username=None,
        name=None,
        email=None,
        followers=0,
        following=1000,  # Extreme follow spam
    )


def make_neutral_user() -> MagicMock:
    """Create a mock user with a neutral profile.

    This represents a typical new but legitimate user.

    Returns:
        MagicMock configured as a neutral GitHub user
    """
    return make_mock_user(
        login="neutral-user",
        created_at=datetime.now(UTC) - relativedelta(months=8),
        avatar_url="https://avatars.githubusercontent.com/u/456",
        bio="Learning to code",
        company=None,
        location="New York",
        blog=None,
        twitter_username=None,
        name="New Developer",
        email=None,
        followers=5,
        following=20,
    )
