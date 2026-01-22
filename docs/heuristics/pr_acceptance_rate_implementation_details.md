# PR Acceptance Rate - Implementation Details

## Overview

This heuristic analyzes a user's pull request history to identify patterns of spam behavior. Users who consistently get PRs rejected, especially in high volumes, are likely spamming.

## Scoring Reference

| Signal | Score | Condition |
|--------|-------|-----------|
| Any month (last 12) with 10+ PRs and <20% merge rate | -25 | High volume spam signal |
| Any month (last 12) with 5+ PRs and <20% merge rate | -15 | Moderate spam signal |
| Overall PR merge rate > 70% (min 5 PRs) | +10 | High-quality contributions |
| Overall PR merge rate > 50% (min 10 PRs) | +5 | Decent track record |

## PyGithub API Usage

### Search API for User's PRs

```python
from github import Github
from datetime import datetime, timedelta

def search_user_prs(g: Github, username: str, since_date: datetime) -> list:
    """
    Search for all PRs created by a user since a given date.

    Uses GitHub Search API: GET /search/issues
    Query: author:{username} type:pr created:>={date}
    """
    date_str = since_date.strftime("%Y-%m-%d")
    query = f"author:{username} type:pr created:>={date_str}"

    # Search returns PaginatedList of Issue objects (PRs are issues)
    results = g.search_issues(query, sort="created", order="desc")
    return list(results)
```

### PR Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `number` | `int` | PR number |
| `state` | `str` | "open", "closed" |
| `created_at` | `datetime` | When PR was created |
| `closed_at` | `datetime \| None` | When PR was closed |
| `merged_at` | `datetime \| None` | When PR was merged (None if not merged) |
| `repository` | `Repository` | The repo this PR belongs to |

**Note**: Search results return `Issue` objects. To check `merged_at`, you need to fetch the PR:

```python
# From search result (Issue object)
issue = search_results[0]
repo = issue.repository
pr = repo.get_pull(issue.number)
is_merged = pr.merged  # or pr.merged_at is not None
```

## Implementation

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from github import Github
from github.NamedUser import NamedUser
import structlog

logger = structlog.get_logger()


@dataclass
class MonthlyPRStats:
    month: str  # "YYYY-MM"
    total: int
    merged: int
    closed_unmerged: int
    open: int
    merge_rate: float


@dataclass
class PRAcceptanceRateResult:
    score: int
    breakdown: dict[str, int]
    overall_stats: dict
    monthly_stats: list[MonthlyPRStats]
    spam_months: list[str]  # Months that triggered spam signals


def get_pr_merge_status(g: Github, issue) -> bool:
    """
    Check if a PR (from search results) was merged.

    Search returns Issue objects, need to fetch actual PR for merge status.
    """
    try:
        repo = issue.repository
        pr = repo.get_pull(issue.number)
        return pr.merged
    except Exception as e:
        logger.warning("failed_to_fetch_pr", issue=issue.number, error=str(e))
        return False


def calculate_pr_acceptance_rate(
    g: Github,
    username: str,
    lookback_months: int = 12,
    reference_date: datetime | None = None,
) -> PRAcceptanceRateResult:
    """
    Calculate PR acceptance rate score for a GitHub user.

    Args:
        g: PyGithub Github instance
        username: GitHub username to analyze
        lookback_months: How many months of history to analyze
        reference_date: Date to calculate from (default: now UTC)

    Returns:
        PRAcceptanceRateResult with score, stats, and breakdown
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    since_date = reference_date - relativedelta(months=lookback_months)

    # Search for user's PRs
    date_str = since_date.strftime("%Y-%m-%d")
    query = f"author:{username} type:pr created:>={date_str}"

    logger.info("searching_user_prs", username=username, query=query)

    try:
        search_results = g.search_issues(query, sort="created", order="desc")
        prs = list(search_results)
    except Exception as e:
        logger.error("pr_search_failed", username=username, error=str(e))
        # Return neutral score on error
        return PRAcceptanceRateResult(
            score=0,
            breakdown={"error": 0},
            overall_stats={"error": str(e)},
            monthly_stats=[],
            spam_months=[],
        )

    if not prs:
        # No PRs found - neutral score
        return PRAcceptanceRateResult(
            score=0,
            breakdown={"no_prs": 0},
            overall_stats={"total": 0},
            monthly_stats=[],
            spam_months=[],
        )

    # Organize PRs by month and fetch merge status
    monthly_data = defaultdict(lambda: {"total": 0, "merged": 0, "closed": 0, "open": 0})
    total_merged = 0
    total_closed = 0
    total_open = 0

    for issue in prs:
        month_key = issue.created_at.strftime("%Y-%m")
        monthly_data[month_key]["total"] += 1

        if issue.state == "open":
            monthly_data[month_key]["open"] += 1
            total_open += 1
        else:
            # Closed PR - check if merged
            is_merged = get_pr_merge_status(g, issue)
            if is_merged:
                monthly_data[month_key]["merged"] += 1
                total_merged += 1
            else:
                monthly_data[month_key]["closed"] += 1
                total_closed += 1

    # Calculate monthly stats
    monthly_stats = []
    spam_months = []

    for month, data in sorted(monthly_data.items()):
        closed_total = data["merged"] + data["closed"]
        merge_rate = data["merged"] / closed_total if closed_total > 0 else 0.0

        stats = MonthlyPRStats(
            month=month,
            total=data["total"],
            merged=data["merged"],
            closed_unmerged=data["closed"],
            open=data["open"],
            merge_rate=round(merge_rate, 2),
        )
        monthly_stats.append(stats)

        # Check for spam patterns
        if data["total"] >= 10 and merge_rate < 0.20:
            spam_months.append(f"{month}:severe")
        elif data["total"] >= 5 and merge_rate < 0.20:
            spam_months.append(f"{month}:moderate")

    # Calculate overall stats
    total_prs = len(prs)
    total_closed_prs = total_merged + total_closed
    overall_merge_rate = total_merged / total_closed_prs if total_closed_prs > 0 else 0.0

    overall_stats = {
        "total": total_prs,
        "merged": total_merged,
        "closed_unmerged": total_closed,
        "open": total_open,
        "merge_rate": round(overall_merge_rate, 2),
    }

    # Calculate score
    score = 0
    breakdown = {}

    # Negative signals: spam months
    severe_spam_months = [m for m in spam_months if "severe" in m]
    moderate_spam_months = [m for m in spam_months if "moderate" in m]

    if severe_spam_months:
        score -= 25
        breakdown["severe_spam_month"] = -25

    elif moderate_spam_months:
        score -= 15
        breakdown["moderate_spam_month"] = -15

    # Positive signals: good merge rate
    if total_prs >= 5 and overall_merge_rate > 0.70:
        score += 10
        breakdown["high_merge_rate"] = 10
    elif total_prs >= 10 and overall_merge_rate > 0.50:
        score += 5
        breakdown["decent_merge_rate"] = 5

    return PRAcceptanceRateResult(
        score=score,
        breakdown=breakdown,
        overall_stats=overall_stats,
        monthly_stats=monthly_stats,
        spam_months=spam_months,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Search user PRs | `g.search_issues(query)` | 30/minute (Search API) |
| Get PR merge status | `repo.get_pull(number)` | 1 request per PR |

**Rate Limit Concern**: For users with many PRs, this can be expensive:
- 100 PRs = 1 search + 100 PR fetches = 101 requests

### Optimization Strategies

```python
def get_pr_merge_status_batch(g: Github, issues: list, max_fetch: int = 50) -> dict:
    """
    Batch fetch PR merge status with limits.

    For high-volume users, sample PRs rather than fetching all.
    """
    results = {}

    # If too many PRs, sample them
    if len(issues) > max_fetch:
        # Sample: take most recent and spread across time range
        sampled = issues[:max_fetch]
    else:
        sampled = issues

    for issue in sampled:
        results[issue.number] = get_pr_merge_status(g, issue)

    return results
```

### Using GraphQL (Alternative)

For better efficiency, use GitHub's GraphQL API to fetch PR data in bulk:

```graphql
query UserPRs($username: String!, $cursor: String) {
  search(query: "author:$username type:pr", type: ISSUE, first: 100, after: $cursor) {
    nodes {
      ... on PullRequest {
        number
        state
        merged
        createdAt
        repository {
          nameWithOwner
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

## Edge Cases

1. **Private PRs**: Search only returns PRs the authenticated app can see. PRs to private repos won't appear unless the app is installed there.

2. **Deleted repos**: PRs to deleted repositories may not be searchable.

3. **Very active users**: Users with thousands of PRs will hit rate limits. Implement sampling.

4. **New users**: Users with <5 PRs don't get positive scores (insufficient data).

5. **All PRs still open**: A user could have 100 open PRs that aren't merged yet. Don't penalize for open PRs.

## Testing Considerations

```python
def test_spam_month_detection():
    """Test spam month detection."""

    # Mock 15 PRs in one month, only 2 merged (13% rate)
    mock_prs = create_mock_prs(
        month="2024-01",
        total=15,
        merged=2,
        closed=13,
    )

    result = calculate_from_mock_prs(mock_prs)
    assert result.score == -25  # Severe spam signal
    assert "2024-01:severe" in result.spam_months


def test_high_merge_rate():
    """Test positive score for good merge rate."""

    # Mock 10 PRs with 80% merge rate
    mock_prs = create_mock_prs(
        total=10,
        merged=8,
        closed=2,
    )

    result = calculate_from_mock_prs(mock_prs)
    assert result.score == 10  # High merge rate bonus
```

## Caching Considerations

PR data changes frequently. Use short TTL:

```python
# Cache key: f"pr_stats:{username}:{lookback_months}"
# TTL: 1-6 hours (balance freshness vs. API usage)
```

Consider caching the raw PR list and recalculating stats from cache.

## Future Improvements

1. **Repository quality weighting**: PRs to popular repos matter more than PRs to personal forks.

2. **Time-weighted scoring**: Recent PR history matters more than old history.

3. **Review feedback analysis**: PRs with extensive review discussions might indicate genuine engagement vs. auto-merged trivial changes.

4. **PR size analysis**: Very small PRs (1-line changes) are more likely to be spam.
