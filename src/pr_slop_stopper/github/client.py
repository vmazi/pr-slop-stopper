"""GitHub API client wrapper for PR Slop Stopper."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

import structlog
from github import Github, RateLimitExceededException
from github.PullRequest import PullRequest
from github.Repository import Repository

from pr_slop_stopper.github.auth import get_installation_client

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds


def with_rate_limit_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry operations when rate limited.

    Uses exponential backoff with jitter.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitExceededException as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "Rate limit exceeded, max retries reached",
                            function=getattr(func, "__name__", str(func)),
                            attempts=attempt + 1,
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2**attempt), max_delay)

                    # Check if GitHub provided a reset time
                    reset_time = getattr(e, "headers", {}).get("X-RateLimit-Reset")
                    if reset_time:
                        try:
                            wait_time = max(0, int(reset_time) - int(time.time()))
                            delay = min(wait_time + 1, max_delay)
                        except (ValueError, TypeError):
                            pass

                    logger.warning(
                        "Rate limit exceeded, retrying",
                        function=getattr(func, "__name__", str(func)),
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=delay,
                    )

                    time.sleep(delay)

            # Should not reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper

    return decorator


@dataclass
class RateLimitInfo:
    """Information about current rate limit status."""

    limit: int
    remaining: int
    reset_timestamp: int
    used: int

    @property
    def reset_in_seconds(self) -> int:
        """Seconds until rate limit resets."""
        return max(0, self.reset_timestamp - int(time.time()))

    @property
    def is_low(self) -> bool:
        """Check if rate limit is getting low (<10% remaining)."""
        return self.remaining < (self.limit * 0.1)

    @property
    def is_exhausted(self) -> bool:
        """Check if rate limit is exhausted."""
        return self.remaining == 0


@dataclass
class GitHubClient:
    """Wrapper around PyGithub for PR Slop Stopper operations."""

    app_id: int
    private_key: str
    installation_id: int
    _client: Github | None = field(default=None, repr=False)

    @property
    def client(self) -> Github:
        """Lazily initialize and return the GitHub client."""
        if self._client is None:
            self._client = get_installation_client(
                self.app_id,
                self.private_key,
                self.installation_id,
            )
        return self._client

    def get_rate_limit(self) -> RateLimitInfo:
        """Get current rate limit status.

        Returns:
            RateLimitInfo with current rate limit details.
        """
        rate_limit = self.client.get_rate_limit()
        core = rate_limit.core  # type: ignore[attr-defined]  # PyGithub stubs incomplete
        return RateLimitInfo(
            limit=core.limit,
            remaining=core.remaining,
            reset_timestamp=int(core.reset.timestamp()),
            used=core.limit - core.remaining,
        )

    def check_rate_limit(self) -> None:
        """Check rate limit and log warning if low.

        Call this before batch operations to avoid hitting limits.
        """
        info = self.get_rate_limit()
        if info.is_exhausted:
            logger.error(
                "GitHub API rate limit exhausted",
                reset_in_seconds=info.reset_in_seconds,
            )
        elif info.is_low:
            logger.warning(
                "GitHub API rate limit is low",
                remaining=info.remaining,
                limit=info.limit,
                reset_in_seconds=info.reset_in_seconds,
            )

    @with_rate_limit_retry()
    def get_repository(self, full_name: str) -> Repository:
        """Get a repository by full name (owner/repo).

        Args:
            full_name: Repository full name like 'owner/repo'.

        Returns:
            The Repository object.
        """
        return self.client.get_repo(full_name)

    @with_rate_limit_retry()
    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest:
        """Get a pull request by repository and PR number.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.

        Returns:
            The PullRequest object.
        """
        repo = self.get_repository(repo_full_name)
        return repo.get_pull(pr_number)

    @with_rate_limit_retry()
    def add_label(self, repo_full_name: str, pr_number: int, label: str) -> None:
        """Add a label to a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
            label: The label name to add.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.add_to_labels(label)

    @with_rate_limit_retry()
    def add_comment(self, repo_full_name: str, pr_number: int, body: str) -> None:
        """Add a comment to a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
            body: The comment body.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.create_issue_comment(body)

    @with_rate_limit_retry()
    def close_pull_request(self, repo_full_name: str, pr_number: int) -> None:
        """Close a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.edit(state="closed")
