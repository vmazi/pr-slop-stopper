"""Comment generation and posting for pull requests."""

import logging

from pr_slop_stopper.core.scorer import ScoringResult
from pr_slop_stopper.types import GitHubClientProtocol

logger = logging.getLogger(__name__)


def generate_comment(result: ScoringResult, username: str) -> str:
    """Generate a comment explaining the reputation score.

    Args:
        result: ScoringResult from the scorer
        username: GitHub username being evaluated

    Returns:
        Markdown formatted comment
    """
    # Header based on recommendation
    if result.recommendation == "close":
        header = "⛔ **PR Slop Stopper: Low Reputation Score**"
        intro = (
            f"The author @{username} has a very low reputation score. "
            "This PR has been flagged as potential spam."
        )
    elif result.recommendation == "warn":
        header = "⚠️ **PR Slop Stopper: Warning**"
        intro = (
            f"The author @{username} has a low reputation score. "
            "Maintainers should review this PR carefully."
        )
    else:
        # This shouldn't happen, but handle it gracefully
        header = "ℹ️ **PR Slop Stopper: Analysis**"
        intro = f"Reputation analysis for @{username}."

    # Score summary
    score_section = f"""
### Score: {result.clamped_score}

| Heuristic | Score |
|-----------|-------|"""

    for name, score in result.breakdown.items():
        sign = "+" if score > 0 else ""
        score_section += f"\n| {_format_heuristic_name(name)} | {sign}{score} |"

    # Details section
    details_section = "\n### Details\n"
    for hr in result.heuristic_results:
        details_section += f"\n**{_format_heuristic_name(hr.name)}**\n"
        for key, value in hr.details.items():
            details_section += f"- {_format_detail_key(key)}: {value}\n"

    # Footer
    footer = """
---
<sub>🤖 This analysis was performed by [PR Slop Stopper](https://github.com/your-org/pr-slop-stopper).
If you believe this is a mistake, please contact the repository maintainers.</sub>
"""

    return f"{header}\n\n{intro}\n{score_section}\n{details_section}\n{footer}"


def _format_heuristic_name(name: str) -> str:
    """Format heuristic name for display.

    Args:
        name: Internal heuristic name (e.g., 'account_age')

    Returns:
        Human-readable name (e.g., 'Account Age')
    """
    return name.replace("_", " ").title()


def _format_detail_key(key: str) -> str:
    """Format detail key for display.

    Args:
        key: Internal detail key (e.g., 'account_age_days')

    Returns:
        Human-readable key (e.g., 'Account Age Days')
    """
    return key.replace("_", " ").title()


def post_comment(
    client: GitHubClientProtocol,
    repo_full_name: str,
    pr_number: int,
    result: ScoringResult,
    username: str,
) -> None:
    """Post a comment to a pull request with the score breakdown.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name (owner/repo)
        pr_number: Pull request number
        result: ScoringResult from the scorer
        username: GitHub username being evaluated
    """
    comment_body = generate_comment(result, username)
    client.add_comment(repo_full_name, pr_number, comment_body)
    logger.info("Posted comment to PR #%d", pr_number)
