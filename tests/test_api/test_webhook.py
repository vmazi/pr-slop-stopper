"""Tests for webhook handler."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from pr_slop_stopper.api.webhook import verify_signature
from pr_slop_stopper.main import app

client = TestClient(app)


class TestVerifySignature:
    """Tests for signature verification."""

    def test_valid_signature(self) -> None:
        """Test valid signature is accepted."""
        secret = "test-secret"
        payload = b'{"test": "payload"}'
        signature = (
            "sha256="
            + hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )

        assert verify_signature(payload, signature, secret) is True

    def test_invalid_signature(self) -> None:
        """Test invalid signature is rejected."""
        secret = "test-secret"
        payload = b'{"test": "payload"}'
        signature = "sha256=invalid"

        assert verify_signature(payload, signature, secret) is False

    def test_missing_signature(self) -> None:
        """Test missing signature is rejected."""
        payload = b'{"test": "payload"}'

        assert verify_signature(payload, "", "secret") is False
        assert verify_signature(payload, None, "secret") is False  # type: ignore[arg-type]

    def test_wrong_prefix(self) -> None:
        """Test signature with wrong prefix is rejected."""
        payload = b'{"test": "payload"}'

        assert verify_signature(payload, "sha1=abc123", "secret") is False


class TestWebhookEndpoint:
    """Tests for the webhook endpoint."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.webhook_secret = "test-webhook-secret"
        self.valid_payload = {
            "action": "opened",
            "number": 1,
            "pull_request": {
                "id": 1,
                "number": 1,
                "title": "Test PR",
                "body": "Test body",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/1",
                "user": {"id": 123, "login": "testuser", "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {
                "id": 456,
                "name": "repo",
                "full_name": "owner/repo",
                "private": False,
                "html_url": "https://github.com/owner/repo",
                "owner": {"id": 789, "login": "owner", "type": "User"},
            },
            "installation": {"id": 999},
            "sender": {"id": 123, "login": "testuser", "type": "User"},
        }

    def _make_signature(self, payload: bytes) -> str:
        """Generate valid signature for payload."""
        return (
            "sha256="
            + hmac.new(
                self.webhook_secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )

    @patch("pr_slop_stopper.config.get_settings")
    def test_invalid_signature_returns_401(self, mock_settings: MagicMock) -> None:
        """Test that invalid signature returns 401."""
        mock_settings.return_value = MagicMock(
            github_webhook_secret=self.webhook_secret,
            github_app_id=12345,
            github_private_key="fake-key",
        )

        response = client.post(
            "/api/webhook/github",
            json=self.valid_payload,
            headers={
                "X-Hub-Signature-256": "sha256=invalid",
                "X-GitHub-Event": "pull_request",
            },
        )

        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]

    @patch("pr_slop_stopper.config.get_settings")
    def test_non_pr_event_ignored(self, mock_settings: MagicMock) -> None:
        """Test that non-PR events are ignored."""
        mock_settings.return_value = MagicMock(
            github_webhook_secret=self.webhook_secret,
            github_app_id=12345,
            github_private_key="fake-key",
        )

        payload_bytes = json.dumps(self.valid_payload).encode()
        signature = self._make_signature(payload_bytes)

        response = client.post(
            "/api/webhook/github",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "push",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert "push" in response.json()["reason"]

    @patch("pr_slop_stopper.config.get_settings")
    def test_non_opened_action_ignored(self, mock_settings: MagicMock) -> None:
        """Test that non-opened actions are ignored."""
        mock_settings.return_value = MagicMock(
            github_webhook_secret=self.webhook_secret,
            github_app_id=12345,
            github_private_key="fake-key",
        )

        payload = {**self.valid_payload, "action": "closed"}
        payload_bytes = json.dumps(payload).encode()
        signature = self._make_signature(payload_bytes)

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
        assert response.json()["status"] == "ignored"
        assert "closed" in response.json()["reason"]

    @patch("pr_slop_stopper.config.get_settings")
    def test_valid_pr_opened_accepted(self, mock_settings: MagicMock) -> None:
        """Test that valid PR opened event returns 200 and queues processing."""
        mock_settings.return_value = MagicMock(
            github_webhook_secret=self.webhook_secret,
            github_app_id=12345,
            github_private_key="fake-key",
        )

        payload_bytes = json.dumps(self.valid_payload).encode()
        signature = self._make_signature(payload_bytes)

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
        assert response.json()["pr"] == 1
