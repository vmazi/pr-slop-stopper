"""Tests for commenter action."""

from pr_slop_stopper.actions.commenter import (
    _format_detail_key,
    _format_heuristic_name,
    generate_comment,
)
from pr_slop_stopper.core.heuristics import HeuristicResult
from pr_slop_stopper.core.scorer import ScoringResult


class TestFormatters:
    """Tests for formatting helper functions."""

    def test_format_heuristic_name(self) -> None:
        """Test heuristic name formatting."""
        assert _format_heuristic_name("account_age") == "Account Age"
        assert _format_heuristic_name("profile_completeness") == "Profile Completeness"
        assert _format_heuristic_name("follower_patterns") == "Follower Patterns"

    def test_format_detail_key(self) -> None:
        """Test detail key formatting."""
        assert _format_detail_key("account_age_days") == "Account Age Days"
        assert _format_detail_key("has_avatar") == "Has Avatar"


class TestGenerateComment:
    """Tests for generate_comment function."""

    def test_warning_comment(self) -> None:
        """Test comment generation for warning recommendation."""
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={"account_age": -10, "profile_completeness": -5},
            heuristic_results=[
                HeuristicResult(
                    name="account_age",
                    score=-10,
                    breakdown={"new": -10},
                    details={"tier": "new", "account_age_days": 45},
                ),
            ],
            recommendation="warn",
        )

        comment = generate_comment(result, "testuser")

        assert "⚠️" in comment
        assert "Warning" in comment
        assert "@testuser" in comment
        assert "-15" in comment
        assert "Account Age" in comment

    def test_close_comment(self) -> None:
        """Test comment generation for close recommendation."""
        result = ScoringResult(
            total_score=-30,
            clamped_score=-30,
            breakdown={"account_age": -20, "follower_patterns": -10},
            heuristic_results=[],
            recommendation="close",
        )

        comment = generate_comment(result, "spammer")

        assert "⛔" in comment
        assert "Low Reputation Score" in comment
        assert "@spammer" in comment
        assert "spam" in comment.lower()

    def test_comment_contains_breakdown_table(self) -> None:
        """Test that comment contains score breakdown table."""
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={"account_age": -10, "profile_completeness": -5},
            heuristic_results=[],
            recommendation="warn",
        )

        comment = generate_comment(result, "user")

        assert "| Heuristic | Score |" in comment
        assert "Account Age" in comment
        assert "-10" in comment

    def test_comment_contains_footer(self) -> None:
        """Test that comment contains footer with attribution."""
        result = ScoringResult(
            total_score=-15,
            clamped_score=-15,
            breakdown={},
            heuristic_results=[],
            recommendation="warn",
        )

        comment = generate_comment(result, "user")

        assert "PR Slop Stopper" in comment
        assert "maintainers" in comment.lower()
