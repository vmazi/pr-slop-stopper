"""Repository configuration loading from .github/pr-slop-stopper.yml."""

import logging
from dataclasses import dataclass, field

import yaml

from pr_slop_stopper.types import GitHubClientProtocol

logger = logging.getLogger(__name__)

CONFIG_FILE_PATH = ".github/pr-slop-stopper.yml"


@dataclass
class RepoConfig:
    """Configuration loaded from repository's pr-slop-stopper.yml file."""

    # Scoring thresholds
    warning_threshold: int = -10
    close_threshold: int = -25

    # Whitelist of usernames to skip
    whitelist: list[str] = field(default_factory=list)

    # Enabled heuristics (None means all)
    enabled_heuristics: list[str] | None = None

    # Action settings
    add_label: bool = True
    add_comment: bool = True
    auto_close: bool = False  # Disabled by default for safety

    # Label names
    warning_label: str = "pr-slop-stopper: warning"
    spam_label: str = "pr-slop-stopper: likely-spam"


def parse_repo_config(content: str) -> RepoConfig:
    """Parse YAML content into RepoConfig.

    Args:
        content: YAML file content

    Returns:
        RepoConfig with parsed values or defaults
    """
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse repo config YAML: %s", e)
        return RepoConfig()

    if not isinstance(data, dict):
        logger.warning("Repo config is not a dictionary")
        return RepoConfig()

    return RepoConfig(
        warning_threshold=data.get("warning_threshold", -10),
        close_threshold=data.get("close_threshold", -25),
        whitelist=data.get("whitelist", []),
        enabled_heuristics=data.get("enabled_heuristics"),
        add_label=data.get("add_label", True),
        add_comment=data.get("add_comment", True),
        auto_close=data.get("auto_close", False),
        warning_label=data.get("warning_label", "pr-slop-stopper: warning"),
        spam_label=data.get("spam_label", "pr-slop-stopper: likely-spam"),
    )


def load_repo_config(client: GitHubClientProtocol, repo_full_name: str) -> RepoConfig:
    """Load configuration from repository's .github/pr-slop-stopper.yml.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name (owner/repo)

    Returns:
        RepoConfig with values from file or defaults
    """
    try:
        repo = client.get_repository(repo_full_name)
        contents = repo.get_contents(CONFIG_FILE_PATH)

        # Handle case where contents might be a list (shouldn't happen for a file)
        if isinstance(contents, list):
            logger.warning("Config path returned multiple files")
            return RepoConfig()

        content = contents.decoded_content.decode("utf-8")
        return parse_repo_config(content)

    except Exception as e:
        # File doesn't exist or other error - use defaults
        logger.debug("Could not load repo config from %s: %s", repo_full_name, e)
        return RepoConfig()
