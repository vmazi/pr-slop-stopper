"""Actions to take on PRs (labeling, commenting, closing)."""

from pr_slop_stopper.actions.commenter import generate_comment, post_comment
from pr_slop_stopper.actions.executor import execute_action
from pr_slop_stopper.actions.labeler import add_spam_label, add_warning_label

__all__ = [
    "add_spam_label",
    "add_warning_label",
    "execute_action",
    "generate_comment",
    "post_comment",
]
