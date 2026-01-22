"""Type definitions for PR Slop Stopper."""

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from github import Github
    from github.PullRequest import PullRequest
    from github.Repository import Repository


class GitHubUserProtocol(Protocol):
    """Protocol defining the GitHub user attributes we need for scoring.

    This allows us to accept both NamedUser and AuthenticatedUser from PyGithub.
    """

    @property
    def login(self) -> str:
        """Username/login."""
        ...

    @property
    def created_at(self) -> datetime:
        """Account creation date."""
        ...

    @property
    def avatar_url(self) -> str | None:
        """Avatar URL."""
        ...

    @property
    def bio(self) -> str | None:
        """User bio."""
        ...

    @property
    def company(self) -> str | None:
        """Company name."""
        ...

    @property
    def location(self) -> str | None:
        """Location string."""
        ...

    @property
    def blog(self) -> str | None:
        """Blog/website URL."""
        ...

    @property
    def twitter_username(self) -> str | None:
        """Twitter username."""
        ...

    @property
    def name(self) -> str | None:
        """Display name."""
        ...

    @property
    def email(self) -> str | None:
        """Public email."""
        ...

    @property
    def followers(self) -> int:
        """Follower count."""
        ...

    @property
    def following(self) -> int:
        """Following count."""
        ...


class GitHubRepositoryProtocol(Protocol):
    """Protocol for Repository objects used in labeler."""

    def get_label(self, name: str) -> object:
        """Get a label by name."""
        ...

    def create_label(
        self,
        name: str,
        color: str,
        description: str = "",
    ) -> object:
        """Create a label."""
        ...


class GitHubClientProtocol(Protocol):
    """Protocol for GitHubClient interface."""

    @property
    def client(self) -> "Github":
        """The underlying PyGithub client."""
        ...

    def get_repository(self, full_name: str) -> "Repository":
        """Get a repository by full name."""
        ...

    def get_pull_request(self, repo_full_name: str, pr_number: int) -> "PullRequest":
        """Get a pull request."""
        ...

    def add_label(self, repo_full_name: str, pr_number: int, label: str) -> None:
        """Add a label to a pull request."""
        ...

    def add_comment(self, repo_full_name: str, pr_number: int, body: str) -> None:
        """Add a comment to a pull request."""
        ...

    def close_pull_request(self, repo_full_name: str, pr_number: int) -> None:
        """Close a pull request."""
        ...
