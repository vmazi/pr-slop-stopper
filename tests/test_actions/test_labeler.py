"""Tests for label management."""

from unittest.mock import MagicMock

from pr_slop_stopper.actions.labeler import (
    SPAM_LABEL_COLOR,
    WARNING_LABEL_COLOR,
    add_spam_label,
    add_warning_label,
    ensure_label_exists,
)


class TestEnsureLabelExists:
    """Tests for ensure_label_exists function."""

    def test_label_already_exists(self) -> None:
        """Test that existing labels are not recreated."""
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = MagicMock()  # Label exists

        ensure_label_exists(mock_repo, "existing-label", "ffffff")

        mock_repo.get_label.assert_called_once_with("existing-label")
        mock_repo.create_label.assert_not_called()

    def test_label_created_when_missing(self) -> None:
        """Test that missing labels are created."""
        mock_repo = MagicMock()
        mock_repo.get_label.side_effect = Exception("Not found")

        ensure_label_exists(mock_repo, "new-label", "ff0000", "Test description")

        mock_repo.create_label.assert_called_once_with(
            name="new-label",
            color="ff0000",
            description="Test description",
        )

    def test_create_label_error_handled(self) -> None:
        """Test that label creation errors are handled gracefully."""
        mock_repo = MagicMock()
        mock_repo.get_label.side_effect = Exception("Not found")
        mock_repo.create_label.side_effect = Exception("Permission denied")

        # Should not raise
        ensure_label_exists(mock_repo, "new-label", "ff0000")


class TestAddWarningLabel:
    """Tests for add_warning_label function."""

    def test_adds_warning_label(self) -> None:
        """Test that warning label is added to PR."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = MagicMock()  # Label exists
        mock_client.get_repository.return_value = mock_repo

        add_warning_label(mock_client, "owner/repo", 123)

        mock_client.add_label.assert_called_once_with("owner/repo", 123, "pr-slop-stopper: warning")

    def test_creates_label_if_missing(self) -> None:
        """Test that warning label is created if it doesn't exist."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.side_effect = Exception("Not found")
        mock_client.get_repository.return_value = mock_repo

        add_warning_label(mock_client, "owner/repo", 123)

        # Should try to create the label
        mock_repo.create_label.assert_called_once()
        create_call = mock_repo.create_label.call_args
        assert create_call[1]["name"] == "pr-slop-stopper: warning"
        assert create_call[1]["color"] == WARNING_LABEL_COLOR

    def test_custom_label_name(self) -> None:
        """Test that custom label names are supported."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = MagicMock()
        mock_client.get_repository.return_value = mock_repo

        add_warning_label(mock_client, "owner/repo", 123, label_name="custom-warning")

        mock_client.add_label.assert_called_once_with("owner/repo", 123, "custom-warning")


class TestAddSpamLabel:
    """Tests for add_spam_label function."""

    def test_adds_spam_label(self) -> None:
        """Test that spam label is added to PR."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = MagicMock()  # Label exists
        mock_client.get_repository.return_value = mock_repo

        add_spam_label(mock_client, "owner/repo", 456)

        mock_client.add_label.assert_called_once_with(
            "owner/repo", 456, "pr-slop-stopper: likely-spam"
        )

    def test_creates_label_if_missing(self) -> None:
        """Test that spam label is created if it doesn't exist."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.side_effect = Exception("Not found")
        mock_client.get_repository.return_value = mock_repo

        add_spam_label(mock_client, "owner/repo", 456)

        # Should try to create the label
        mock_repo.create_label.assert_called_once()
        create_call = mock_repo.create_label.call_args
        assert create_call[1]["name"] == "pr-slop-stopper: likely-spam"
        assert create_call[1]["color"] == SPAM_LABEL_COLOR

    def test_custom_label_name(self) -> None:
        """Test that custom label names are supported."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = MagicMock()
        mock_client.get_repository.return_value = mock_repo

        add_spam_label(mock_client, "owner/repo", 456, label_name="spam-detected")

        mock_client.add_label.assert_called_once_with("owner/repo", 456, "spam-detected")


class TestLabelColors:
    """Tests for label color constants."""

    def test_warning_label_color_is_yellow(self) -> None:
        """Test warning label has yellow color."""
        assert WARNING_LABEL_COLOR == "fbca04"

    def test_spam_label_color_is_red(self) -> None:
        """Test spam label has red color."""
        assert SPAM_LABEL_COLOR == "d93f0b"
