"""Tests for GitHub models."""

from pr_slop_stopper.github.models import (
    GitHubUser,
    InstallationInfo,
    RepositoryInfo,
    ScoreResult,
)


def test_github_user_creation() -> None:
    """Test GitHubUser model can be created with required fields."""
    user = GitHubUser(id=1, login="testuser")
    assert user.id == 1
    assert user.login == "testuser"
    assert user.type == "User"


def test_github_user_with_all_fields() -> None:
    """Test GitHubUser model with all optional fields."""
    user = GitHubUser(
        id=1,
        login="testuser",
        avatar_url="https://example.com/avatar.png",
        html_url="https://github.com/testuser",
        type="Bot",
    )
    assert user.avatar_url == "https://example.com/avatar.png"
    assert user.html_url == "https://github.com/testuser"
    assert user.type == "Bot"


def test_repository_info() -> None:
    """Test RepositoryInfo model creation."""
    owner = GitHubUser(id=1, login="owner")
    repo = RepositoryInfo(
        id=100,
        name="test-repo",
        full_name="owner/test-repo",
        private=False,
        html_url="https://github.com/owner/test-repo",
        owner=owner,
    )
    assert repo.full_name == "owner/test-repo"
    assert repo.owner.login == "owner"


def test_installation_info() -> None:
    """Test InstallationInfo model creation."""
    installation = InstallationInfo(id=12345)
    assert installation.id == 12345


def test_score_result() -> None:
    """Test ScoreResult model creation."""
    result = ScoreResult(
        total_score=15,
        breakdown={"account_age": 10, "profile": 5},
        details={"account_age": "Account is 3 years old", "profile": "Has bio and avatar"},
        recommendation="allow",
    )
    assert result.total_score == 15
    assert result.recommendation == "allow"
    assert "account_age" in result.breakdown
