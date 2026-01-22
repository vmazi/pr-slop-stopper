"""Tests for action executor."""

from unittest.mock import MagicMock, patch

import pytest

from pr_slop_stopper.actions.executor import execute_action
from pr_slop_stopper.core.repo_config import RepoConfig
from pr_slop_stopper.core.scorer import ScoringResult


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GitHub client."""
    client = MagicMock()
    mock_pr = MagicMock()
    mock_pr.user.login = "testuser"
    client.get_pull_request.return_value = mock_pr
    return client


@pytest.fixture
def default_config() -> RepoConfig:
    """Create default repo config."""
    return RepoConfig()


class TestExecuteAction:
    """Tests for execute_action function."""

    @pytest.mark.asyncio
    async def test_allow_does_nothing(
        self,
        mock_client: MagicMock,
        default_config: RepoConfig,
    ) -> None:
        """Test that 'allow' recommendation does nothing."""
        result = ScoringResult(
            total_score=10,
            clamped_score=10,
            breakdown={},
            heuristic_results=[],
            recommendation="allow",
        )

        with patch("pr_slop_stopper.actions.executor.add_warning_label") as mock_label:
            with patch("pr_slop_stopper.actions.executor.post_comment") as mock_comment:
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    default_config,
                )

        mock_label.assert_not_called()
        mock_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_warn_adds_label_and_comment(
        self,
        mock_client: MagicMock,
        default_config: RepoConfig,
    ) -> None:
        """Test that 'warn' recommendation adds label and comment."""
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={},
            heuristic_results=[],
            recommendation="warn",
        )

        with patch("pr_slop_stopper.actions.executor.add_warning_label") as mock_label:
            with patch("pr_slop_stopper.actions.executor.post_comment") as mock_comment:
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    default_config,
                )

        mock_label.assert_called_once()
        mock_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_adds_spam_label(
        self,
        mock_client: MagicMock,
        default_config: RepoConfig,
    ) -> None:
        """Test that 'close' recommendation adds spam label."""
        result = ScoringResult(
            total_score=-30,
            clamped_score=-30,
            breakdown={},
            heuristic_results=[],
            recommendation="close",
        )

        with patch("pr_slop_stopper.actions.executor.add_spam_label") as mock_label:
            with patch("pr_slop_stopper.actions.executor.post_comment"):
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    default_config,
                )

        mock_label.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_does_not_auto_close_by_default(
        self,
        mock_client: MagicMock,
        default_config: RepoConfig,
    ) -> None:
        """Test that auto_close is disabled by default."""
        result = ScoringResult(
            total_score=-30,
            clamped_score=-30,
            breakdown={},
            heuristic_results=[],
            recommendation="close",
        )

        with patch("pr_slop_stopper.actions.executor.add_spam_label"):
            with patch("pr_slop_stopper.actions.executor.post_comment"):
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    default_config,
                )

        mock_client.close_pull_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_auto_closes_when_enabled(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test that auto_close works when enabled."""
        config = RepoConfig(auto_close=True)
        result = ScoringResult(
            total_score=-30,
            clamped_score=-30,
            breakdown={},
            heuristic_results=[],
            recommendation="close",
        )

        with patch("pr_slop_stopper.actions.executor.add_spam_label"):
            with patch("pr_slop_stopper.actions.executor.post_comment"):
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    config,
                )

        mock_client.close_pull_request.assert_called_once_with("owner/repo", 1)

    @pytest.mark.asyncio
    async def test_respects_add_label_false(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test that add_label=False disables labeling."""
        config = RepoConfig(add_label=False)
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={},
            heuristic_results=[],
            recommendation="warn",
        )

        with patch("pr_slop_stopper.actions.executor.add_warning_label") as mock_label:
            with patch("pr_slop_stopper.actions.executor.post_comment"):
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    config,
                )

        mock_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_respects_add_comment_false(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test that add_comment=False disables commenting."""
        config = RepoConfig(add_comment=False)
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={},
            heuristic_results=[],
            recommendation="warn",
        )

        with patch("pr_slop_stopper.actions.executor.add_warning_label"):
            with patch("pr_slop_stopper.actions.executor.post_comment") as mock_comment:
                await execute_action(
                    mock_client,
                    "owner/repo",
                    1,
                    result,
                    config,
                )

        mock_comment.assert_not_called()
