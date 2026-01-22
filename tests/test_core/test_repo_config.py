"""Tests for repo config loading."""

from unittest.mock import MagicMock

from pr_slop_stopper.core.repo_config import (
    RepoConfig,
    load_repo_config,
    parse_repo_config,
)


class TestParseRepoConfig:
    """Tests for parse_repo_config function."""

    def test_empty_content(self) -> None:
        """Test empty YAML returns defaults."""
        config = parse_repo_config("")
        assert config.warning_threshold == -10
        assert config.close_threshold == -25
        assert config.whitelist == []

    def test_invalid_yaml(self) -> None:
        """Test invalid YAML returns defaults."""
        config = parse_repo_config("invalid: yaml: content: [")
        assert config.warning_threshold == -10

    def test_non_dict_yaml(self) -> None:
        """Test non-dict YAML returns defaults."""
        config = parse_repo_config("- item1\n- item2")
        assert config.warning_threshold == -10

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        content = """
warning_threshold: -5
close_threshold: -20
"""
        config = parse_repo_config(content)
        assert config.warning_threshold == -5
        assert config.close_threshold == -20

    def test_whitelist(self) -> None:
        """Test whitelist parsing."""
        content = """
whitelist:
  - dependabot[bot]
  - renovate[bot]
  - trusted-user
"""
        config = parse_repo_config(content)
        assert "dependabot[bot]" in config.whitelist
        assert "renovate[bot]" in config.whitelist
        assert "trusted-user" in config.whitelist

    def test_enabled_heuristics(self) -> None:
        """Test enabled_heuristics parsing."""
        content = """
enabled_heuristics:
  - account_age
  - profile_completeness
"""
        config = parse_repo_config(content)
        assert config.enabled_heuristics == ["account_age", "profile_completeness"]

    def test_all_heuristics_by_default(self) -> None:
        """Test that all heuristics are enabled by default (None)."""
        config = parse_repo_config("")
        assert config.enabled_heuristics is None

    def test_action_settings(self) -> None:
        """Test action settings parsing."""
        content = """
add_label: false
add_comment: true
auto_close: true
"""
        config = parse_repo_config(content)
        assert config.add_label is False
        assert config.add_comment is True
        assert config.auto_close is True

    def test_auto_close_disabled_by_default(self) -> None:
        """Test auto_close is disabled by default."""
        config = parse_repo_config("")
        assert config.auto_close is False

    def test_custom_labels(self) -> None:
        """Test custom label names."""
        content = """
warning_label: "needs-review"
spam_label: "spam"
"""
        config = parse_repo_config(content)
        assert config.warning_label == "needs-review"
        assert config.spam_label == "spam"


class TestRepoConfig:
    """Tests for RepoConfig dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = RepoConfig()
        assert config.warning_threshold == -10
        assert config.close_threshold == -25
        assert config.whitelist == []
        assert config.enabled_heuristics is None
        assert config.add_label is True
        assert config.add_comment is True
        assert config.auto_close is False
        assert config.warning_label == "pr-slop-stopper: warning"
        assert config.spam_label == "pr-slop-stopper: likely-spam"


class TestLoadRepoConfig:
    """Tests for load_repo_config function."""

    def test_file_not_found_returns_defaults(self) -> None:
        """Test missing config file returns defaults."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = Exception("Not found")
        mock_client.get_repository.return_value = mock_repo

        config = load_repo_config(mock_client, "owner/repo")

        assert config.warning_threshold == -10
        assert config.close_threshold == -25

    def test_valid_config_loaded(self) -> None:
        """Test valid config file is loaded and parsed."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_contents = MagicMock()
        mock_contents.decoded_content = b"""
warning_threshold: -15
whitelist:
  - bot-user
"""
        mock_repo.get_contents.return_value = mock_contents
        mock_client.get_repository.return_value = mock_repo

        config = load_repo_config(mock_client, "owner/repo")

        assert config.warning_threshold == -15
        assert "bot-user" in config.whitelist
