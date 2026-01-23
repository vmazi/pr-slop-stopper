"""Action executor for PR scoring results."""

import logging

from pr_slop_stopper.actions.commenter import post_comment
from pr_slop_stopper.actions.labeler import (
    add_passed_label,
    add_spam_label,
    add_warning_label,
)
from pr_slop_stopper.core.repo_config import RepoConfig
from pr_slop_stopper.core.scorer import ScoringResult
from pr_slop_stopper.types import GitHubClientProtocol

logger = logging.getLogger(__name__)


async def execute_action(
    client: GitHubClientProtocol,
    repo_full_name: str,
    pr_number: int,
    result: ScoringResult,
    config: RepoConfig,
) -> None:
    """Execute appropriate actions based on scoring result.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name (owner/repo)
        pr_number: Pull request number
        result: ScoringResult from the scorer
        config: RepoConfig with action settings
    """
    # Get PR author username for comments
    pr = client.get_pull_request(repo_full_name, pr_number)
    username = pr.user.login

    if result.recommendation == "allow":
        logger.info("PR #%d allowed (score: %d)", pr_number, result.clamped_score)

        if config.add_passed_label:
            try:
                add_passed_label(client, repo_full_name, pr_number, config.passed_label)
            except Exception:
                logger.exception("Failed to add passed label to PR #%d", pr_number)

        return

    if result.recommendation == "warn":
        logger.info("PR #%d flagged for warning (score: %d)", pr_number, result.clamped_score)

        if config.add_label:
            try:
                add_warning_label(client, repo_full_name, pr_number, config.warning_label)
            except Exception:
                logger.exception("Failed to add warning label to PR #%d", pr_number)

        if config.add_comment:
            try:
                post_comment(client, repo_full_name, pr_number, result, username)
            except Exception:
                logger.exception("Failed to post comment to PR #%d", pr_number)

    elif result.recommendation == "close":
        logger.info("PR #%d flagged as spam (score: %d)", pr_number, result.clamped_score)

        if config.add_label:
            try:
                add_spam_label(client, repo_full_name, pr_number, config.spam_label)
            except Exception:
                logger.exception("Failed to add spam label to PR #%d", pr_number)

        if config.add_comment:
            try:
                post_comment(client, repo_full_name, pr_number, result, username)
            except Exception:
                logger.exception("Failed to post comment to PR #%d", pr_number)

        if config.auto_close:
            try:
                client.close_pull_request(repo_full_name, pr_number)
                logger.info("Closed PR #%d", pr_number)
            except Exception:
                logger.exception("Failed to close PR #%d", pr_number)
