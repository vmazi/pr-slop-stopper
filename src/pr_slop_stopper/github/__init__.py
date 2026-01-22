"""GitHub API client and authentication."""

from pr_slop_stopper.github.auth import get_installation_client
from pr_slop_stopper.github.client import GitHubClient
from pr_slop_stopper.github.models import (
    GitHubUser,
    InstallationInfo,
    PullRequestInfo,
    PullRequestWebhookPayload,
    RepositoryInfo,
    ScoreResult,
)

__all__ = [
    "get_installation_client",
    "GitHubClient",
    "GitHubUser",
    "InstallationInfo",
    "PullRequestInfo",
    "PullRequestWebhookPayload",
    "RepositoryInfo",
    "ScoreResult",
]
