# Activity Patterns - Implementation Details

## Overview

This heuristic analyzes a user's GitHub activity patterns to detect suspicious behavior. Legitimate developers typically show consistent activity over time, while spam accounts often show bursts of activity or unusual patterns.

## Scoring Reference

| Signal | Score | Detection Method |
|--------|-------|------------------|
| Consistent activity over 2+ years | +10 | Event history analysis |
| Regular commits to own repos | +5 | Repository commit activity |
| Burst of activity after years dormant | -15 | Event timeline gaps |
| 10+ PRs in a year to repos with <10K stars | -10 | PR target analysis |
| Fork created <24h before PR | -10 | Fork timestamp vs PR timestamp |
| PRs only to repos never starred/engaged | -8 | User starred repos vs PR targets |

## PyGithub API Usage

### User Events

```python
from github import Github

def get_user_events(g: Github, username: str) -> list:
    """
    Get user's public activity events.

    Events include: PushEvent, PullRequestEvent, IssuesEvent,
    CreateEvent, ForkEvent, WatchEvent, etc.

    Note: GitHub only retains events for 90 days.
    """
    user = g.get_user(username)
    events = user.get_public_events()
    return list(events)
```

### User Repositories

```python
def get_user_repos(g: Github, username: str) -> list:
    """Get user's repositories with commit activity."""
    user = g.get_user(username)
    repos = user.get_repos(type="owner", sort="updated")
    return list(repos)
```

### Starred Repositories

```python
def get_starred_repos(g: Github, username: str) -> set:
    """Get set of repos the user has starred."""
    user = g.get_user(username)
    starred = user.get_starred()
    return {repo.full_name for repo in starred}
```

## Implementation

```python
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from github import Github
from github.NamedUser import NamedUser
import structlog

logger = structlog.get_logger()


@dataclass
class ActivityPatternsResult:
    score: int
    breakdown: dict[str, int]
    details: dict


def analyze_event_consistency(events: list) -> tuple[bool, bool, dict]:
    """
    Analyze event timeline for consistency and dormancy patterns.

    Returns:
        - is_consistent: True if activity spans 2+ years
        - has_dormancy_burst: True if sudden activity after long gap
        - stats: Dictionary with analysis details
    """
    if not events:
        return False, False, {"total_events": 0}

    # Events are returned newest first
    event_dates = [e.created_at for e in events]

    if not event_dates:
        return False, False, {"total_events": 0}

    newest = max(event_dates)
    oldest = min(event_dates)
    span_days = (newest - oldest).days

    # Group events by month
    monthly_activity = defaultdict(int)
    for date in event_dates:
        month_key = date.strftime("%Y-%m")
        monthly_activity[month_key] += 1

    # Check for consistency (2+ years of activity)
    is_consistent = span_days >= 730  # ~2 years

    # Check for dormancy burst pattern
    # Look for gaps of 6+ months followed by sudden activity
    has_dormancy_burst = False
    sorted_months = sorted(monthly_activity.keys())

    if len(sorted_months) >= 2:
        for i in range(1, len(sorted_months)):
            prev_month = datetime.strptime(sorted_months[i-1], "%Y-%m")
            curr_month = datetime.strptime(sorted_months[i], "%Y-%m")
            gap_months = (curr_month.year - prev_month.year) * 12 + (curr_month.month - prev_month.month)

            if gap_months >= 6:
                # Check if recent activity is high
                recent_months = sorted_months[i:]
                recent_activity = sum(monthly_activity[m] for m in recent_months)
                if recent_activity >= 20:  # High activity after gap
                    has_dormancy_burst = True
                    break

    stats = {
        "total_events": len(events),
        "span_days": span_days,
        "months_active": len(monthly_activity),
        "is_consistent": is_consistent,
        "has_dormancy_burst": has_dormancy_burst,
    }

    return is_consistent, has_dormancy_burst, stats


def check_own_repo_activity(g: Github, username: str) -> tuple[bool, dict]:
    """
    Check if user has regular commits to their own repositories.

    Returns:
        - has_regular_commits: True if user actively maintains own repos
        - stats: Dictionary with analysis details
    """
    try:
        user = g.get_user(username)
        repos = list(user.get_repos(type="owner", sort="pushed"))[:20]  # Check recent 20

        repos_with_commits = 0
        total_recent_commits = 0

        for repo in repos:
            if repo.fork:
                continue  # Skip forks

            try:
                # Check for recent commits by this user
                commits = repo.get_commits(author=username)
                commit_count = 0
                for commit in commits[:10]:  # Sample first 10
                    commit_count += 1
                    if commit_count >= 5:
                        break

                if commit_count > 0:
                    repos_with_commits += 1
                    total_recent_commits += commit_count
            except Exception:
                continue  # Repo might be empty or inaccessible

        has_regular_commits = repos_with_commits >= 2 and total_recent_commits >= 10

        stats = {
            "repos_checked": len(repos),
            "repos_with_commits": repos_with_commits,
            "total_recent_commits": total_recent_commits,
        }

        return has_regular_commits, stats

    except Exception as e:
        logger.warning("own_repo_check_failed", username=username, error=str(e))
        return False, {"error": str(e)}


def check_low_star_pr_spam(g: Github, username: str) -> tuple[bool, dict]:
    """
    Check if user opens many PRs to low-star repos (gaming metrics).

    Signal: 10+ PRs in a year to repos with <10K stars

    Returns:
        - is_gaming: True if pattern detected
        - stats: Dictionary with analysis details
    """
    try:
        # Search for user's PRs in the last year
        one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
        query = f"author:{username} type:pr created:>={one_year_ago}"
        results = g.search_issues(query)

        low_star_prs = 0
        high_star_prs = 0
        checked = 0

        for issue in results:
            if checked >= 50:  # Limit checks
                break

            try:
                repo = issue.repository
                stars = repo.stargazers_count

                if stars < 10000:
                    low_star_prs += 1
                else:
                    high_star_prs += 1

                checked += 1
            except Exception:
                continue

        # Gaming pattern: many PRs to low-star repos, few to high-star
        is_gaming = low_star_prs >= 10 and high_star_prs < 3

        stats = {
            "low_star_prs": low_star_prs,
            "high_star_prs": high_star_prs,
            "checked": checked,
        }

        return is_gaming, stats

    except Exception as e:
        logger.warning("low_star_check_failed", username=username, error=str(e))
        return False, {"error": str(e)}


def check_drive_by_prs(g: Github, username: str) -> tuple[bool, dict]:
    """
    Check if user's PRs are to repos they've never engaged with.

    Signal: PRs only to repos never starred or previously contributed to

    Returns:
        - is_drive_by: True if pattern detected
        - stats: Dictionary with analysis details
    """
    try:
        user = g.get_user(username)

        # Get starred repos
        starred = {repo.full_name for repo in user.get_starred()}

        # Get recent PRs
        query = f"author:{username} type:pr"
        results = g.search_issues(query)

        pr_repos = set()
        for issue in list(results)[:30]:  # Check last 30 PRs
            try:
                pr_repos.add(issue.repository.full_name)
            except Exception:
                continue

        # Check overlap
        engaged_repos = pr_repos.intersection(starred)
        drive_by_repos = pr_repos - starred

        # Pattern: Most PRs to repos never starred
        total_pr_repos = len(pr_repos)
        is_drive_by = (
            total_pr_repos >= 5 and
            len(drive_by_repos) / total_pr_repos > 0.8
        )

        stats = {
            "pr_repos": len(pr_repos),
            "starred_repos": len(starred),
            "engaged_repos": len(engaged_repos),
            "drive_by_repos": len(drive_by_repos),
        }

        return is_drive_by, stats

    except Exception as e:
        logger.warning("drive_by_check_failed", username=username, error=str(e))
        return False, {"error": str(e)}


def check_fork_timing(g: Github, username: str, pr_repo: str, pr_created: datetime) -> tuple[bool, dict]:
    """
    Check if user forked the repo immediately before opening PR.

    Signal: Fork created <24h before PR

    This is called per-PR being analyzed, not for overall user scoring.

    Returns:
        - is_quick_fork: True if fork was very recent
        - stats: Dictionary with timing details
    """
    try:
        user = g.get_user(username)

        # Look for user's fork of this repo
        repo_name = pr_repo.split("/")[-1]

        for repo in user.get_repos(type="owner"):
            if repo.fork and repo.name == repo_name:
                # Found the fork
                fork_created = repo.created_at
                if fork_created.tzinfo is None:
                    fork_created = fork_created.replace(tzinfo=timezone.utc)

                time_diff = pr_created - fork_created
                hours_diff = time_diff.total_seconds() / 3600

                is_quick_fork = hours_diff < 24

                return is_quick_fork, {
                    "fork_created": fork_created.isoformat(),
                    "pr_created": pr_created.isoformat(),
                    "hours_diff": round(hours_diff, 2),
                }

        return False, {"fork_found": False}

    except Exception as e:
        logger.warning("fork_timing_check_failed", username=username, error=str(e))
        return False, {"error": str(e)}


def calculate_activity_patterns(
    g: Github,
    username: str,
) -> ActivityPatternsResult:
    """
    Calculate activity patterns score for a GitHub user.

    Args:
        g: PyGithub Github instance
        username: GitHub username to analyze

    Returns:
        ActivityPatternsResult with score, breakdown, and details
    """
    score = 0
    breakdown = {}
    details = {}

    # 1. Check event consistency
    try:
        user = g.get_user(username)
        events = list(user.get_public_events())
        is_consistent, has_dormancy_burst, event_stats = analyze_event_consistency(events)
        details["events"] = event_stats

        if is_consistent:
            score += 10
            breakdown["consistent_activity"] = 10

        if has_dormancy_burst:
            score -= 15
            breakdown["dormancy_burst"] = -15

    except Exception as e:
        logger.warning("event_analysis_failed", username=username, error=str(e))
        details["events"] = {"error": str(e)}

    # 2. Check own repo activity
    has_regular_commits, repo_stats = check_own_repo_activity(g, username)
    details["own_repos"] = repo_stats

    if has_regular_commits:
        score += 5
        breakdown["own_repo_activity"] = 5

    # 3. Check low-star PR spam pattern
    is_gaming, gaming_stats = check_low_star_pr_spam(g, username)
    details["low_star_prs"] = gaming_stats

    if is_gaming:
        score -= 10
        breakdown["low_star_pr_spam"] = -10

    # 4. Check drive-by PR pattern
    is_drive_by, drive_by_stats = check_drive_by_prs(g, username)
    details["drive_by"] = drive_by_stats

    if is_drive_by:
        score -= 8
        breakdown["drive_by_prs"] = -8

    return ActivityPatternsResult(
        score=score,
        breakdown=breakdown,
        details=details,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Get user events | `user.get_public_events()` | 1 request (paginated) |
| Get user repos | `user.get_repos()` | 1 request (paginated) |
| Get repo commits | `repo.get_commits()` | 1 per repo checked |
| Get starred repos | `user.get_starred()` | 1 request (paginated) |
| Search user PRs | `g.search_issues()` | 30/minute limit |

**Estimated total**: 5-25 requests depending on user activity level

## Edge Cases

1. **Event retention**: GitHub only retains events for 90 days. Can't detect dormancy patterns older than that from events alone.

2. **Private activity**: Private repo activity isn't visible. A user might be very active in private repos.

3. **Organization activity**: Activity in org repos might not show in personal events.

4. **New but legitimate users**: A new user with a burst of activity might be legitimately excited about open source.

5. **Bot accounts**: Bots often have very consistent, high-volume activity that could be mistaken for good patterns.

## Testing Considerations

```python
def test_dormancy_burst_detection():
    """Test detection of activity after dormancy."""
    # Mock events showing gap then burst
    mock_events = [
        MockEvent(created_at=datetime(2024, 1, 15)),  # Recent
        MockEvent(created_at=datetime(2024, 1, 10)),  # Recent
        # ... 20 more events in January 2024
        MockEvent(created_at=datetime(2023, 1, 1)),   # Old, gap of 1 year
    ]

    is_consistent, has_dormancy, stats = analyze_event_consistency(mock_events)
    assert has_dormancy == True


def test_low_star_gaming():
    """Test detection of low-star repo targeting."""
    # Mock PRs to low-star repos
    result = check_low_star_pr_spam_with_mock(
        prs=[
            {"repo": "user1/small-project", "stars": 50},
            {"repo": "user2/another-small", "stars": 200},
            # ... 10 more to low-star repos
        ]
    )
    assert result[0] == True  # is_gaming
```

## Caching Considerations

Activity patterns change frequently:

```python
# Cache key: f"activity_patterns:{username}"
# TTL: 6-12 hours (activity changes but not minute-by-minute)
```

## Future Improvements

1. **Contribution graph analysis**: Use GitHub's contribution graph data for longer-term patterns.

2. **Commit timing analysis**: Unusual commit times (e.g., every commit at exactly midnight) could indicate automation.

3. **Commit message analysis**: Repetitive or templated commit messages might indicate automation.

4. **Cross-reference with PR content**: Combine with PR diff analysis to detect copy-paste patterns.
