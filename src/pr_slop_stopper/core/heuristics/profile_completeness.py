"""Profile completeness heuristic implementation."""

import re
from datetime import datetime

from github import Github

from pr_slop_stopper.core.heuristics.base import (
    BaseHeuristic,
    DetailValue,
    HeuristicResult,
    registry,
)
from pr_slop_stopper.types import GitHubUserProtocol


def is_default_avatar(avatar_url: str | None) -> bool:
    """Check if avatar is GitHub's default identicon."""
    if not avatar_url:
        return True
    if "identicon" in avatar_url.lower():
        return True
    return False


def extract_linkedin_url(blog: str | None) -> str | None:
    """Extract LinkedIn URL if present in blog field."""
    if not blog:
        return None
    linkedin_pattern = r"linkedin\.com/in/([a-zA-Z0-9-]+)"
    match = re.search(linkedin_pattern, blog.lower())
    if match:
        return match.group(0)
    return None


def name_matches_linkedin(name: str | None, linkedin_url: str | None) -> bool:
    """Check if user's name loosely matches their LinkedIn profile slug."""
    if not name or not linkedin_url:
        return False

    match = re.search(r"linkedin\.com/in/([a-zA-Z0-9-]+)", linkedin_url.lower())
    if not match:
        return False

    slug = match.group(1).replace("-", "").replace("_", "")
    name_parts = name.lower().split()

    if len(name_parts) >= 2:
        first = name_parts[0].replace("-", "")
        last = name_parts[-1].replace("-", "")
        return first in slug and last in slug

    name_normalized = name.lower().replace(" ", "").replace("-", "")
    return name_normalized in slug or slug in name_normalized


class ProfileCompletenessHeuristic(BaseHeuristic):
    """Evaluates profile completeness to detect low-effort accounts."""

    @property
    def name(self) -> str:
        return "profile_completeness"

    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
        github_client: Github | None = None,
    ) -> HeuristicResult:
        """Evaluate profile completeness score.

        Args:
            user: GitHub user object
            reference_date: Not used, but required by base class
            github_client: GitHub client (unused by this heuristic)

        Returns:
            HeuristicResult with profile completeness score
        """
        score = 0
        breakdown: dict[str, int] = {}
        details: dict[str, DetailValue] = {
            "has_avatar": False,
            "has_bio": False,
            "has_company": False,
            "has_location": False,
            "has_blog": False,
            "has_linkedin": False,
            "has_twitter": False,
        }

        # Check profile picture
        if user.avatar_url and not is_default_avatar(user.avatar_url):
            score += 5
            breakdown["profile_picture"] = 5
            details["has_avatar"] = True
        else:
            score -= 5
            breakdown["no_profile_picture"] = -5

        # Check bio
        if user.bio and len(user.bio.strip()) > 0:
            score += 3
            breakdown["bio"] = 3
            details["has_bio"] = True

        # Check company
        if user.company and len(user.company.strip()) > 0:
            score += 3
            breakdown["company"] = 3
            details["has_company"] = True

        # Check location
        if user.location and len(user.location.strip()) > 0:
            score += 2
            breakdown["location"] = 2
            details["has_location"] = True

        # Check blog/website
        if user.blog and len(user.blog.strip()) > 0:
            score += 3
            breakdown["blog"] = 3
            details["has_blog"] = True

            # Check for LinkedIn link
            linkedin_url = extract_linkedin_url(user.blog)
            if linkedin_url:
                if name_matches_linkedin(user.name, linkedin_url):
                    score += 5
                    breakdown["linkedin_match"] = 5
                    details["has_linkedin"] = True

        # Check Twitter
        if user.twitter_username and len(user.twitter_username.strip()) > 0:
            score += 2
            breakdown["twitter"] = 2
            details["has_twitter"] = True

        # Penalty: No bio AND no links
        has_any_link = (
            details["has_blog"]
            or details["has_twitter"]
            or (user.email and len(user.email.strip()) > 0)
        )
        if not details["has_bio"] and not has_any_link:
            score -= 5
            breakdown["empty_profile_penalty"] = -5

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown=breakdown,
            details=details,
        )


# Register the heuristic
registry.register(ProfileCompletenessHeuristic())
