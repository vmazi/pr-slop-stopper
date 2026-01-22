"""Integration tests for the full webhook → score → action flow."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pr_slop_stopper.main import app
from tests.fixtures.user_profiles import (
    make_good_user,
    make_spam_user,
    make_suspicious_user,
)
from tests.fixtures.webhook_payloads import make_pr_opened_payload


class TestFullFlow:
    """Test the complete webhook → score → action flow."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def webhook_secret(self) -> str:
        """Webhook secret for tests."""
        return "test-webhook-secret"

    @pytest.fixture
    def mock_settings(self, webhook_secret: str) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.github_app_id = 12345
        settings.github_private_key = "fake-private-key"
        settings.github_webhook_secret = webhook_secret
        return settings

    def _make_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Generate valid signature for payload."""
        return (
            "sha256="
            + hmac.new(
                secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
        )

    def test_good_user_allowed(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that a good user is allowed without labels or comments."""
        payload = make_pr_opened_payload(
            sender_login="good-contributor",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.user.login = "good-contributor"
        mock_repo.has_in_collaborators.return_value = False

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.get_pull_request.return_value = mock_pr
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=0)
        mock_github_client.client.get_user.return_value = make_good_user()

        # Mock repo config (no config file)
        mock_repo.get_contents.side_effect = Exception("File not found")

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_spam_user_flagged(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that a spam user gets labeled and commented on."""
        payload = make_pr_opened_payload(
            sender_login="spam-account",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.user.login = "spam-account"
        mock_repo.has_in_collaborators.return_value = False

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.get_pull_request.return_value = mock_pr
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=0)
        mock_github_client.client.get_user.return_value = make_spam_user()

        # Mock repo config (no config file)
        mock_repo.get_contents.side_effect = Exception("File not found")

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_suspicious_user_warned(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that a suspicious user gets a warning label."""
        payload = make_pr_opened_payload(
            sender_login="suspicious-user",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.user.login = "suspicious-user"
        mock_repo.has_in_collaborators.return_value = False

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.get_pull_request.return_value = mock_pr
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=0)
        mock_github_client.client.get_user.return_value = make_suspicious_user()

        # Mock repo config (no config file)
        mock_repo.get_contents.side_effect = Exception("File not found")

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_collaborator_skipped(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that collaborators are skipped from scoring."""
        payload = make_pr_opened_payload(
            sender_login="maintainer",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.has_in_collaborators.return_value = True  # User is collaborator

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=0)

        # Mock repo config (no config file)
        mock_repo.get_contents.side_effect = Exception("File not found")

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        # get_user should not be called for collaborators
        mock_github_client.client.get_user.assert_not_called()

    def test_whitelisted_user_skipped(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that whitelisted users are skipped from scoring."""
        payload = make_pr_opened_payload(
            sender_login="trusted-bot",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_contents = MagicMock()
        mock_contents.decoded_content = b"whitelist:\n  - trusted-bot\n"

        mock_repo.has_in_collaborators.return_value = False
        mock_repo.get_contents.return_value = mock_contents

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=0)

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        # get_user should not be called for whitelisted users
        mock_github_client.client.get_user.assert_not_called()

    def test_previously_merged_user_skipped(
        self, client: TestClient, mock_settings: MagicMock, webhook_secret: str
    ) -> None:
        """Test that users with previously merged PRs are skipped."""
        payload = make_pr_opened_payload(
            sender_login="returning-contributor",
            repo_full_name="owner/repo",
        )
        payload_bytes = json.dumps(payload).encode()

        # Create mocks
        mock_github_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.has_in_collaborators.return_value = False

        # User has previously merged PRs
        mock_github_client.client.search_issues.return_value = MagicMock(totalCount=5)
        mock_github_client.get_repository.return_value = mock_repo

        # Mock repo config (no config file)
        mock_repo.get_contents.side_effect = Exception("File not found")

        with (
            patch("pr_slop_stopper.config.get_settings", return_value=mock_settings),
            patch(
                "pr_slop_stopper.github.GitHubClient",
                return_value=mock_github_client,
            ),
        ):
            signature = self._make_signature(payload_bytes, webhook_secret)
            response = client.post(
                "/api/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        # get_user should not be called for users with merged PRs
        mock_github_client.client.get_user.assert_not_called()


class TestScoringIntegration:
    """Test scoring integration with all heuristics."""

    def test_score_aggregation(self) -> None:
        """Test that all heuristics contribute to the final score."""
        from pr_slop_stopper.core import ReputationScorer

        scorer = ReputationScorer()
        user = make_good_user()

        result = scorer.calculate_score(user)

        # Good user should have positive score
        assert result.clamped_score > 0
        assert result.recommendation == "allow"
        # Should have results from all three heuristics
        assert "account_age" in result.breakdown
        assert "profile_completeness" in result.breakdown
        assert "follower_patterns" in result.breakdown

    def test_spam_detection(self) -> None:
        """Test that spam accounts are detected."""
        from pr_slop_stopper.core import ReputationScorer

        scorer = ReputationScorer()
        user = make_spam_user()

        result = scorer.calculate_score(user)

        # Spam user should have very negative score
        assert result.clamped_score < -25
        assert result.recommendation == "close"

    def test_suspicious_warning(self) -> None:
        """Test that suspicious accounts get warnings."""
        from pr_slop_stopper.core import ReputationScorer

        scorer = ReputationScorer()
        user = make_suspicious_user()

        result = scorer.calculate_score(user)

        # Suspicious user should have negative score but not spam-level
        assert result.clamped_score < 0
        assert result.recommendation in ["warn", "close"]
