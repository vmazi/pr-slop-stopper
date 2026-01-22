# Follower Patterns - Implementation Details

## Overview

This heuristic analyzes a user's follower/following patterns on GitHub. Legitimate developers often have organic follower growth, while spam or bot accounts often exhibit follow-spam patterns (following many users to get follow-backs, with poor results).

## Scoring Reference

| Signal | Score | Condition |
|--------|-------|-----------|
| 50+ followers | +8 | `followers >= 50` |
| 20+ followers | +5 | `followers >= 20` |
| 5+ followers | +2 | `followers >= 5` |
| Following 500+ but <10 followers | -10 | `following >= 500 AND followers < 10` |
| Following/follower ratio > 50:1 | -8 | `following / followers > 50` |

**Note**: Positive scores are mutually exclusive (only highest applies). Negative scores can stack.

## PyGithub API Usage

### Required Data

```python
from github import Github

def get_follower_stats(g: Github, username: str) -> dict:
    """Fetch follower/following counts."""
    user = g.get_user(username)
    return {
        "followers": user.followers,
        "following": user.following,
    }
```

### Available Fields from PyGithub NamedUser

| Field | Type | Description |
|-------|------|-------------|
| `followers` | `int` | Number of users following this account |
| `following` | `int` | Number of users this account follows |

## Implementation

```python
from dataclasses import dataclass
from github.NamedUser import NamedUser


@dataclass
class FollowerPatternsResult:
    score: int
    breakdown: dict[str, int]
    followers: int
    following: int
    ratio: float | None
    tier: str


def calculate_follower_patterns(user: NamedUser) -> FollowerPatternsResult:
    """
    Calculate follower patterns score for a GitHub user.

    Args:
        user: PyGithub NamedUser object

    Returns:
        FollowerPatternsResult with score and pattern details
    """
    followers = user.followers
    following = user.following

    score = 0
    breakdown = {}

    # Calculate ratio (avoid division by zero)
    if followers > 0:
        ratio = following / followers
    else:
        ratio = float('inf') if following > 0 else 0

    # Positive signals (mutually exclusive - take highest)
    if followers >= 50:
        score += 8
        breakdown["high_followers"] = 8
        tier = "popular"
    elif followers >= 20:
        score += 5
        breakdown["moderate_followers"] = 5
        tier = "recognized"
    elif followers >= 5:
        score += 2
        breakdown["some_followers"] = 2
        tier = "basic"
    else:
        tier = "minimal"

    # Negative signals (can stack)

    # Pattern 1: Following many but almost no followers (follow spam)
    if following >= 500 and followers < 10:
        score -= 10
        breakdown["follow_spam_extreme"] = -10

    # Pattern 2: Very high following/follower ratio
    elif ratio > 50 and following > 100:
        # Only apply if they're actually following a significant number
        # (ratio of 50:1 with 50 following and 1 follower is less suspicious
        #  than 5000 following and 100 followers)
        score -= 8
        breakdown["high_follow_ratio"] = -8

    return FollowerPatternsResult(
        score=score,
        breakdown=breakdown,
        followers=followers,
        following=following,
        ratio=round(ratio, 2) if ratio != float('inf') else None,
        tier=tier,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Get user profile | `g.get_user(username)` | 1 request |

**Total requests**: 1 (same call as profile completeness - can be shared)

## Alternative: Detailed Follower Analysis

For more sophisticated analysis, you can fetch actual follower/following lists:

```python
def get_detailed_follower_analysis(g: Github, username: str, sample_size: int = 100) -> dict:
    """
    Analyze follower quality (expensive - use sparingly).

    This fetches actual follower accounts to analyze their quality.
    """
    user = g.get_user(username)

    # Sample followers
    followers = list(user.get_followers())[:sample_size]
    following = list(user.get_following())[:sample_size]

    # Analyze follower quality
    follower_stats = {
        "total": user.followers,
        "sampled": len(followers),
        "with_bio": sum(1 for f in followers if f.bio),
        "with_repos": sum(1 for f in followers if f.public_repos > 0),
        "avg_followers": sum(f.followers for f in followers) / len(followers) if followers else 0,
    }

    # Check for mutual follows (often indicates follow-back schemes)
    follower_logins = {f.login for f in followers}
    following_logins = {f.login for f in following}
    mutual = follower_logins.intersection(following_logins)

    return {
        "follower_stats": follower_stats,
        "mutual_follow_count": len(mutual),
        "mutual_follow_rate": len(mutual) / len(followers) if followers else 0,
    }
```

**Warning**: This is expensive (1 request per follower fetched) and should only be used for edge cases.

## Edge Cases

1. **New accounts**: A new account with 0 followers is normal. Don't penalize just for having few followers.

2. **Corporate accounts**: Some corporate accounts follow no one but have many followers. This is fine.

3. **Private following**: The following count includes private users, but you can't see who they are.

4. **Organization accounts**: Org accounts typically don't follow anyone. Check `user.type == "Organization"`.

5. **Very popular users**: Users with 10K+ followers might follow many people back as a courtesy.

## Testing Considerations

```python
def test_follower_tiers():
    """Test follower tier scoring."""
    test_cases = [
        # (followers, following, expected_score, expected_tier)
        (100, 50, 8, "popular"),      # 50+ followers
        (30, 100, 5, "recognized"),   # 20+ followers
        (8, 20, 2, "basic"),          # 5+ followers
        (2, 10, 0, "minimal"),        # <5 followers
    ]

    for followers, following, expected_score, expected_tier in test_cases:
        user = MockUser(followers=followers, following=following)
        result = calculate_follower_patterns(user)
        assert result.score == expected_score
        assert result.tier == expected_tier


def test_follow_spam_detection():
    """Test follow spam pattern detection."""

    # Extreme follow spam
    user = MockUser(followers=5, following=1000)
    result = calculate_follower_patterns(user)
    assert "follow_spam_extreme" in result.breakdown
    assert result.score < 0

    # High ratio but not extreme
    user = MockUser(followers=10, following=600)
    result = calculate_follower_patterns(user)
    assert "high_follow_ratio" in result.breakdown


def test_normal_patterns():
    """Test that normal patterns aren't penalized."""

    # New user
    user = MockUser(followers=0, following=5)
    result = calculate_follower_patterns(user)
    assert result.score == 0  # No penalty for new users

    # Active follower
    user = MockUser(followers=100, following=200)
    result = calculate_follower_patterns(user)
    assert result.score == 8  # Gets bonus, no penalty
```

## Caching Considerations

Follower counts change slowly:

```python
# Cache key: f"follower_patterns:{username}"
# TTL: 12-24 hours (followers don't change rapidly)
```

## Score Calculation Summary

```
Final Score = (Positive Tier Score) + (Negative Pattern Penalties)

Example 1: Popular user with normal patterns
  - 100 followers, 50 following
  - Positive: +8 (popular tier)
  - Negative: none
  - Final: +8

Example 2: Follow spammer
  - 5 followers, 800 following
  - Positive: +2 (basic tier, 5 followers)
  - Negative: -10 (follow spam extreme)
  - Final: -8

Example 3: High ratio but not extreme
  - 20 followers, 1500 following (75:1 ratio)
  - Positive: +5 (recognized tier)
  - Negative: -8 (high ratio)
  - Final: -3
```

## Future Improvements

1. **Follower quality scoring**: Analyze if followers are real accounts or also potential bots.

2. **Follower growth rate**: Sudden spikes in followers could indicate purchased followers.

3. **Network analysis**: Check if followers form a tight cluster (bot network) or are diverse.

4. **Mutual follow analysis**: High mutual follow rates might indicate follow-for-follow schemes.

5. **Time-based analysis**: When did the user gain most followers? Organic growth vs. sudden spike.
