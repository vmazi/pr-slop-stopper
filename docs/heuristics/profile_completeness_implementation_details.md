# Profile Completeness - Implementation Details

## Overview

This heuristic evaluates how complete a GitHub user's profile is. Legitimate contributors typically invest time in their profile, while spam accounts often have minimal information.

## Scoring Reference

| Signal | Score | Field(s) Used |
|--------|-------|---------------|
| Has profile picture (not default) | +5 | `avatar_url` |
| Has bio/description | +3 | `bio` |
| Has company/organization listed | +3 | `company` |
| Has location | +2 | `location` |
| Has website/blog link | +3 | `blog` |
| Has LinkedIn link matching name | +5 | `blog` (parse URL) |
| Has Twitter/X link | +2 | `twitter_username` |
| No profile picture | -5 | `avatar_url` |
| No bio AND no links | -5 | `bio`, `blog`, `twitter_username` |

## PyGithub API Usage

### Required Data

```python
from github import Github

def get_user_profile(g: Github, username: str) -> dict:
    """Fetch user profile data needed for scoring."""
    user = g.get_user(username)
    return {
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "company": user.company,
        "location": user.location,
        "blog": user.blog,
        "twitter_username": user.twitter_username,
        "name": user.name,
        "email": user.email,
    }
```

### Available Fields from PyGithub NamedUser

| Field | Type | Description |
|-------|------|-------------|
| `avatar_url` | `str` | URL to profile picture |
| `bio` | `str \| None` | Profile bio text |
| `company` | `str \| None` | Company name |
| `location` | `str \| None` | Location string |
| `blog` | `str \| None` | Website URL |
| `twitter_username` | `str \| None` | Twitter handle |
| `name` | `str \| None` | Display name |
| `email` | `str \| None` | Public email |

## Implementation

```python
from dataclasses import dataclass
from github import Github
from github.NamedUser import NamedUser
import re


@dataclass
class ProfileCompletenessResult:
    score: int
    breakdown: dict[str, int]
    details: dict[str, any]


def is_default_avatar(avatar_url: str) -> bool:
    """
    Check if avatar is GitHub's default (identicon/gravatar).

    Default avatars follow patterns like:
    - https://avatars.githubusercontent.com/u/12345?v=4 (no custom avatar)
    - Contains 'identicon' in URL
    - Gravatar default patterns
    """
    if not avatar_url:
        return True

    # GitHub generates default avatars at avatars.githubusercontent.com
    # Custom avatars also use this domain, but we can check for identicon param
    # or use heuristics based on the URL structure

    # If URL contains identicon, it's definitely default
    if "identicon" in avatar_url.lower():
        return True

    # GitHub default avatars are generated SVGs or identicons
    # This is a simplified check - may need refinement based on actual patterns
    return False


def extract_linkedin_url(blog: str | None) -> str | None:
    """Extract LinkedIn URL if present in blog field."""
    if not blog:
        return None

    linkedin_pattern = r'linkedin\.com/in/([a-zA-Z0-9-]+)'
    match = re.search(linkedin_pattern, blog.lower())
    if match:
        return match.group(0)
    return None


def name_matches_linkedin(name: str | None, linkedin_url: str | None) -> bool:
    """
    Check if user's name loosely matches their LinkedIn profile slug.

    This is a heuristic check - LinkedIn slugs are often derived from names.
    Example: "John Smith" might have linkedin.com/in/johnsmith or john-smith
    """
    if not name or not linkedin_url:
        return False

    # Extract the slug from LinkedIn URL
    match = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', linkedin_url.lower())
    if not match:
        return False

    slug = match.group(1).replace("-", "").replace("_", "")
    name_normalized = name.lower().replace(" ", "").replace("-", "")

    # Check if name parts appear in slug
    name_parts = name.lower().split()
    if len(name_parts) >= 2:
        # Check if first and last name appear in slug
        first = name_parts[0].replace("-", "")
        last = name_parts[-1].replace("-", "")
        return first in slug and last in slug

    # Single name - check direct containment
    return name_normalized in slug or slug in name_normalized


def calculate_profile_completeness(user: NamedUser) -> ProfileCompletenessResult:
    """
    Calculate profile completeness score for a GitHub user.

    Args:
        user: PyGithub NamedUser object

    Returns:
        ProfileCompletenessResult with score, breakdown, and details
    """
    score = 0
    breakdown = {}
    details = {
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
        details["has_blog"] or
        details["has_twitter"] or
        (user.email and len(user.email.strip()) > 0)
    )
    if not details["has_bio"] and not has_any_link:
        score -= 5
        breakdown["empty_profile_penalty"] = -5

    return ProfileCompletenessResult(
        score=score,
        breakdown=breakdown,
        details=details,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Get user profile | `g.get_user(username)` | 1 request |

**Total requests**: 1

## Edge Cases

1. **Gravatar detection**: GitHub uses Gravatar for some default avatars. May need to check Gravatar API or use heuristics.

2. **LinkedIn in bio vs blog**: Some users put LinkedIn in their bio text rather than the blog field. Could extend to parse bio for URLs.

3. **Multiple social links**: Users may have multiple links. Consider checking bio text for additional social profiles.

4. **Unicode names**: Name matching with LinkedIn should handle unicode characters properly.

5. **Private email**: The `email` field only contains publicly visible emails. Many users keep this private.

## Testing Considerations

```python
def test_profile_completeness():
    """Test cases for profile completeness scoring."""

    # Mock user with complete profile
    complete_user = MockUser(
        avatar_url="https://avatars.githubusercontent.com/u/123?custom=true",
        bio="Software engineer passionate about open source",
        company="@acme-corp",
        location="San Francisco, CA",
        blog="https://linkedin.com/in/johndoe",
        twitter_username="johndoe",
        name="John Doe",
    )
    result = calculate_profile_completeness(complete_user)
    assert result.score == 23  # Max positive score

    # Mock user with empty profile
    empty_user = MockUser(
        avatar_url=None,
        bio=None,
        company=None,
        location=None,
        blog=None,
        twitter_username=None,
        name=None,
    )
    result = calculate_profile_completeness(empty_user)
    assert result.score == -10  # Max negative score
```

## Future Improvements

1. **Profile picture analysis**: Use image analysis to detect stock photos or AI-generated images
2. **Bio quality scoring**: Check bio length, language quality, presence of keywords
3. **Social link verification**: Actually verify that linked profiles exist and match
4. **Organization membership**: Check if user belongs to reputable GitHub orgs
