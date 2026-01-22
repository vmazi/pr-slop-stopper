"""Label management for pull requests."""

import logging

from pr_slop_stopper.types import GitHubClientProtocol, GitHubRepositoryProtocol

logger = logging.getLogger(__name__)

# Label colors (GitHub hex without #)
WARNING_LABEL_COLOR = "fbca04"  # Yellow
SPAM_LABEL_COLOR = "d93f0b"  # Red


def ensure_label_exists(
    repo: GitHubRepositoryProtocol,
    label_name: str,
    color: str,
    description: str = "",
) -> None:
    """Ensure a label exists in the repository, creating it if needed.

    Args:
        repo: PyGithub Repository object
        label_name: Name of the label
        color: Hex color code (without #)
        description: Optional label description
    """
    try:
        repo.get_label(label_name)
        logger.debug("Label '%s' already exists", label_name)
    except Exception:
        # Label doesn't exist, create it
        try:
            repo.create_label(
                name=label_name,
                color=color,
                description=description,
            )
            logger.info("Created label '%s'", label_name)
        except Exception as e:
            logger.warning("Failed to create label '%s': %s", label_name, e)


def add_warning_label(
    client: GitHubClientProtocol,
    repo_full_name: str,
    pr_number: int,
    label_name: str = "pr-slop-stopper: warning",
) -> None:
    """Add warning label to a pull request.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name (owner/repo)
        pr_number: Pull request number
        label_name: Name of the warning label
    """
    repo = client.get_repository(repo_full_name)

    # Ensure label exists
    ensure_label_exists(
        repo,
        label_name,
        WARNING_LABEL_COLOR,
        "PR author has low reputation score - review carefully",
    )

    # Add label to PR
    client.add_label(repo_full_name, pr_number, label_name)
    logger.info("Added warning label to PR #%d", pr_number)


def add_spam_label(
    client: GitHubClientProtocol,
    repo_full_name: str,
    pr_number: int,
    label_name: str = "pr-slop-stopper: likely-spam",
) -> None:
    """Add spam label to a pull request.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name (owner/repo)
        pr_number: Pull request number
        label_name: Name of the spam label
    """
    repo = client.get_repository(repo_full_name)

    # Ensure label exists
    ensure_label_exists(
        repo,
        label_name,
        SPAM_LABEL_COLOR,
        "PR author has very low reputation score - likely spam",
    )

    # Add label to PR
    client.add_label(repo_full_name, pr_number, label_name)
    logger.info("Added spam label to PR #%d", pr_number)
