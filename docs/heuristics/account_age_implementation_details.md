# Account Age - Implementation Details

## Overview

This heuristic evaluates the age of a GitHub account. Newer accounts are more likely to be throwaway spam accounts, while established accounts have more reputation to lose.

## Scoring Reference

| Signal | Score | Condition |
|--------|-------|-----------|
| Account age >= 5 years | +15 | `created_at` <= 5 years ago |
| Account age >= 3 years | +10 | `created_at` <= 3 years ago |
| Account age >= 1 year | +5 | `created_at` <= 1 year ago |
| Account age >= 6 months | 0 | `created_at` <= 6 months ago |
| Account age < 6 months | -10 | `created_at` > 6 months ago |
| Account age < 3 months | -15 | `created_at` > 3 months ago |
| Account age < 1 month | -20 | `created_at` > 1 month ago |

**Note**: Only the single most applicable score is applied (not cumulative).

## PyGithub API Usage

### Required Data

```python
from github import Github
from datetime import datetime

def get_account_creation_date(g: Github, username: str) -> datetime:
    """Fetch account creation date."""
    user = g.get_user(username)
    return user.created_at
```

### Available Fields from PyGithub NamedUser

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | `datetime` | Account creation timestamp (UTC) |
| `updated_at` | `datetime` | Last profile update timestamp |

## Implementation

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from github.NamedUser import NamedUser


@dataclass
class AccountAgeResult:
    score: int
    account_age_days: int
    account_age_months: int
    account_age_years: float
    created_at: datetime
    tier: str


def calculate_account_age(
    user: NamedUser,
    reference_date: datetime | None = None
) -> AccountAgeResult:
    """
    Calculate account age score for a GitHub user.

    Args:
        user: PyGithub NamedUser object
        reference_date: Date to calculate age from (default: now UTC)

    Returns:
        AccountAgeResult with score and age details
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    created_at = user.created_at
    if created_at.tzinfo is None:
        # PyGithub returns naive datetime, assume UTC
        created_at = created_at.replace(tzinfo=timezone.utc)

    # Calculate age
    age_delta = relativedelta(reference_date, created_at)
    age_days = (reference_date - created_at).days
    age_months = age_delta.years * 12 + age_delta.months
    age_years = age_days / 365.25

    # Determine score tier (most specific match wins)
    if age_days < 30:  # Less than 1 month
        score = -20
        tier = "very_new"
    elif age_days < 90:  # Less than 3 months
        score = -15
        tier = "new"
    elif age_months < 6:  # Less than 6 months
        score = -10
        tier = "recent"
    elif age_years < 1:  # Less than 1 year
        score = 0
        tier = "neutral"
    elif age_years < 3:  # 1-3 years
        score = 5
        tier = "established"
    elif age_years < 5:  # 3-5 years
        score = 10
        tier = "mature"
    else:  # 5+ years
        score = 15
        tier = "veteran"

    return AccountAgeResult(
        score=score,
        account_age_days=age_days,
        account_age_months=age_months,
        account_age_years=round(age_years, 2),
        created_at=created_at,
        tier=tier,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Get user profile | `g.get_user(username)` | 1 request |

**Total requests**: 1 (same call as profile completeness - can be shared)

## Edge Cases

1. **Timezone handling**: GitHub returns UTC timestamps. Ensure consistent timezone handling.

2. **Leap years**: Use `365.25` for year calculations or `relativedelta` for accuracy.

3. **Very old accounts**: GitHub was founded in 2008. Accounts older than that are impossible.

4. **Account suspension history**: A very old account that was recently unsuspended might still be suspicious (not detectable via API).

## Testing Considerations

```python
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta


def test_account_age_tiers():
    """Test all account age tiers."""
    now = datetime(2024, 6, 15, tzinfo=timezone.utc)

    test_cases = [
        # (created_at, expected_score, expected_tier)
        (now - relativedelta(days=15), -20, "very_new"),
        (now - relativedelta(months=2), -15, "new"),
        (now - relativedelta(months=4), -10, "recent"),
        (now - relativedelta(months=8), 0, "neutral"),
        (now - relativedelta(years=2), 5, "established"),
        (now - relativedelta(years=4), 10, "mature"),
        (now - relativedelta(years=6), 15, "veteran"),
    ]

    for created_at, expected_score, expected_tier in test_cases:
        user = MockUser(created_at=created_at)
        result = calculate_account_age(user, reference_date=now)
        assert result.score == expected_score
        assert result.tier == expected_tier


def test_account_age_boundary():
    """Test boundary conditions."""
    now = datetime(2024, 6, 15, tzinfo=timezone.utc)

    # Exactly 1 month old
    user = MockUser(created_at=now - relativedelta(months=1))
    result = calculate_account_age(user, reference_date=now)
    assert result.score == -15  # Falls into 1-3 month range

    # Exactly 5 years old
    user = MockUser(created_at=now - relativedelta(years=5))
    result = calculate_account_age(user, reference_date=now)
    assert result.score == 15  # Veteran tier
```

## Caching Considerations

Account age is **immutable** - `created_at` never changes. This makes it an excellent candidate for long-term caching:

```python
# Cache key: f"account_age:{user_id}"
# TTL: 30 days (or longer - value never changes)
```

## Future Improvements

1. **Activity relative to age**: An account created 5 years ago but with activity only in the last month could indicate a purchased/compromised account.

2. **First contribution date**: When did the user make their first public contribution? Large gap between account creation and first activity is suspicious.

3. **Account ID analysis**: GitHub user IDs are sequential. Very high IDs relative to creation date could indicate batch account creation.
