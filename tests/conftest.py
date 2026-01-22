"""Pytest configuration and fixtures."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from pr_slop_stopper.github.models import (
    GitHubUser,
    InstallationInfo,
    PullRequestWebhookPayload,
    RepositoryInfo,
)


@pytest.fixture
def sample_github_user() -> GitHubUser:
    """Create a sample GitHub user for testing."""
    return GitHubUser(
        id=12345,
        login="test-user",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        html_url="https://github.com/test-user",
        type="User",
    )


@pytest.fixture
def sample_repository() -> RepositoryInfo:
    """Create a sample repository for testing."""
    return RepositoryInfo(
        id=67890,
        name="test-repo",
        full_name="owner/test-repo",
        private=False,
        html_url="https://github.com/owner/test-repo",
        owner=GitHubUser(
            id=11111,
            login="owner",
            type="User",
        ),
    )


@pytest.fixture
def sample_webhook_payload(
    sample_github_user: GitHubUser,
    sample_repository: RepositoryInfo,
) -> PullRequestWebhookPayload:
    """Create a sample webhook payload for testing."""
    return PullRequestWebhookPayload(
        action="opened",
        number=1,
        pull_request={
            "id": 1,
            "number": 1,
            "title": "Test PR",
            "body": "Test body",
            "state": "open",
            "html_url": "https://github.com/owner/test-repo/pull/1",
            "user": sample_github_user.model_dump(),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
        repository=sample_repository,
        installation=InstallationInfo(id=99999),
        sender=sample_github_user,
    )


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mock GitHub client for testing."""
    return MagicMock()
