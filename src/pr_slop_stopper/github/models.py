"""Data models for GitHub webhook payloads and PR analysis."""

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user information from webhook payload."""

    id: int
    login: str
    avatar_url: str | None = None
    html_url: str | None = None
    type: str = "User"  # "User" or "Bot"


class PullRequestInfo(BaseModel):
    """Pull request information from webhook payload."""

    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    html_url: str
    user: GitHubUser
    created_at: datetime
    updated_at: datetime
    head_sha: str = Field(alias="head.sha", default="")
    base_ref: str = Field(alias="base.ref", default="")


class RepositoryInfo(BaseModel):
    """Repository information from webhook payload."""

    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    owner: GitHubUser


class InstallationInfo(BaseModel):
    """GitHub App installation information."""

    id: int


class PullRequestWebhookPayload(BaseModel):
    """Webhook payload for pull_request events."""

    action: str
    number: int
    pull_request: dict  # Raw PR data, complex nested structure
    repository: RepositoryInfo
    installation: InstallationInfo
    sender: GitHubUser


class ScoreResult(BaseModel):
    """Result of reputation scoring for a PR author."""

    total_score: int
    breakdown: dict[str, int]
    details: dict[str, str]
    recommendation: str  # "allow", "warn", or "close"
