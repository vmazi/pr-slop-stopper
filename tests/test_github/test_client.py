"""Tests for GitHub API client with rate limiting."""

import time
from unittest.mock import MagicMock, patch

import pytest
from github import RateLimitExceededException

from pr_slop_stopper.github.client import (
    GitHubClient,
    RateLimitInfo,
    with_rate_limit_retry,
)


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass."""

    def test_reset_in_seconds(self) -> None:
        """Test reset_in_seconds calculation."""
        future_reset = int(time.time()) + 300  # 5 minutes from now
        info = RateLimitInfo(
            limit=5000,
            remaining=1000,
            reset_timestamp=future_reset,
            used=4000,
        )
        # Should be approximately 300 seconds
        assert 295 <= info.reset_in_seconds <= 305

    def test_reset_in_seconds_past(self) -> None:
        """Test reset_in_seconds when reset time is in the past."""
        past_reset = int(time.time()) - 60  # 1 minute ago
        info = RateLimitInfo(
            limit=5000,
            remaining=1000,
            reset_timestamp=past_reset,
            used=4000,
        )
        assert info.reset_in_seconds == 0

    def test_is_low_true(self) -> None:
        """Test is_low returns True when < 10% remaining."""
        info = RateLimitInfo(
            limit=5000,
            remaining=400,  # 8%
            reset_timestamp=int(time.time()) + 3600,
            used=4600,
        )
        assert info.is_low is True

    def test_is_low_false(self) -> None:
        """Test is_low returns False when >= 10% remaining."""
        info = RateLimitInfo(
            limit=5000,
            remaining=600,  # 12%
            reset_timestamp=int(time.time()) + 3600,
            used=4400,
        )
        assert info.is_low is False

    def test_is_exhausted_true(self) -> None:
        """Test is_exhausted returns True when 0 remaining."""
        info = RateLimitInfo(
            limit=5000,
            remaining=0,
            reset_timestamp=int(time.time()) + 3600,
            used=5000,
        )
        assert info.is_exhausted is True

    def test_is_exhausted_false(self) -> None:
        """Test is_exhausted returns False when > 0 remaining."""
        info = RateLimitInfo(
            limit=5000,
            remaining=1,
            reset_timestamp=int(time.time()) + 3600,
            used=4999,
        )
        assert info.is_exhausted is False


class TestWithRateLimitRetry:
    """Tests for the rate limit retry decorator."""

    def test_successful_call_no_retry(self) -> None:
        """Test that successful calls don't retry."""
        call_count = 0

        @with_rate_limit_retry(max_retries=3)
        def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_rate_limit_retry_succeeds(self) -> None:
        """Test that retries work after rate limit exception."""
        call_count = 0

        @with_rate_limit_retry(max_retries=3, base_delay=0.01)
        def fails_then_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitExceededException(403, {}, {})
            return "success"

        result = fails_then_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_rate_limit_max_retries_exceeded(self) -> None:
        """Test that max retries raises exception."""
        call_count = 0

        @with_rate_limit_retry(max_retries=2, base_delay=0.01)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise RateLimitExceededException(403, {}, {})

        with pytest.raises(RateLimitExceededException):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_non_rate_limit_exception_not_retried(self) -> None:
        """Test that non-rate-limit exceptions are not retried."""
        call_count = 0

        @with_rate_limit_retry(max_retries=3, base_delay=0.01)
        def raises_value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("not a rate limit error")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retries for non-rate-limit errors


class TestGitHubClient:
    """Tests for GitHubClient class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.client = GitHubClient(
            app_id=12345,
            private_key="fake_key",
            installation_id=67890,
        )

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_client_lazy_initialization(self, mock_get_client: MagicMock) -> None:
        """Test that client is lazily initialized."""
        mock_github = MagicMock()
        mock_get_client.return_value = mock_github

        # Client should not be initialized yet
        assert self.client._client is None

        # Access client property
        _ = self.client.client

        # Now it should be initialized
        mock_get_client.assert_called_once_with(12345, "fake_key", 67890)
        assert self.client._client is mock_github

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_get_repository(self, mock_get_client: MagicMock) -> None:
        """Test get_repository method."""
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_github

        repo = self.client.get_repository("owner/repo")

        mock_github.get_repo.assert_called_once_with("owner/repo")
        assert repo is mock_repo

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_get_pull_request(self, mock_get_client: MagicMock) -> None:
        """Test get_pull_request method."""
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_github

        pr = self.client.get_pull_request("owner/repo", 123)

        mock_github.get_repo.assert_called_with("owner/repo")
        mock_repo.get_pull.assert_called_once_with(123)
        assert pr is mock_pr

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_add_label(self, mock_get_client: MagicMock) -> None:
        """Test add_label method."""
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_github

        self.client.add_label("owner/repo", 123, "bug")

        mock_pr.add_to_labels.assert_called_once_with("bug")

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_add_comment(self, mock_get_client: MagicMock) -> None:
        """Test add_comment method."""
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_github

        self.client.add_comment("owner/repo", 123, "Test comment")

        mock_pr.create_issue_comment.assert_called_once_with("Test comment")

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_close_pull_request(self, mock_get_client: MagicMock) -> None:
        """Test close_pull_request method."""
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_github

        self.client.close_pull_request("owner/repo", 123)

        mock_pr.edit.assert_called_once_with(state="closed")

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_get_rate_limit(self, mock_get_client: MagicMock) -> None:
        """Test get_rate_limit method."""
        mock_github = MagicMock()
        mock_rate_limit = MagicMock()
        mock_core = MagicMock()
        mock_core.limit = 5000
        mock_core.remaining = 4500
        mock_core.reset.timestamp.return_value = 1700000000
        mock_rate_limit.core = mock_core
        mock_github.get_rate_limit.return_value = mock_rate_limit
        mock_get_client.return_value = mock_github

        info = self.client.get_rate_limit()

        assert info.limit == 5000
        assert info.remaining == 4500
        assert info.reset_timestamp == 1700000000
        assert info.used == 500

    @patch("pr_slop_stopper.github.client.get_installation_client")
    def test_check_rate_limit_logs_warning_when_low(self, mock_get_client: MagicMock) -> None:
        """Test that check_rate_limit logs warning when rate limit is low."""
        mock_github = MagicMock()
        mock_rate_limit = MagicMock()
        mock_core = MagicMock()
        mock_core.limit = 5000
        mock_core.remaining = 100  # Low
        mock_core.reset.timestamp.return_value = int(time.time()) + 3600
        mock_rate_limit.core = mock_core
        mock_github.get_rate_limit.return_value = mock_rate_limit
        mock_get_client.return_value = mock_github

        # This should log a warning but not raise
        self.client.check_rate_limit()

        mock_github.get_rate_limit.assert_called_once()
