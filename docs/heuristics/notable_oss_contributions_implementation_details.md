# Notable OSS Contributions - Implementation Details

## Overview

This heuristic awards positive reputation for contributions to well-known, reputable open source organizations. Getting a PR merged into Apache, Linux, or Kubernetes demonstrates that the user has been vetted by discerning maintainers.

## Scoring Reference

| Signal | Score | Organizations |
|--------|-------|---------------|
| Merged PR to Apache project | +15 | `apache/*` |
| Merged PR to Linux Foundation | +15 | `torvalds/linux`, `linuxfoundation/*` |
| Merged PR to CNCF project | +12 | `cncf/*`, `kubernetes/*`, `prometheus/*`, `envoyproxy/*` |
| Merged PR to Mozilla | +12 | `mozilla/*` |
| Merged PR to Kubernetes | +12 | `kubernetes/*` |
| Merged PR to Rust | +10 | `rust-lang/*` |
| Merged PR to Python | +10 | `python/*` |
| Merged PR to Node.js | +10 | `nodejs/*` |
| Merged PR to Django | +8 | `django/*` |
| Merged PR to Rails | +8 | `rails/*` |
| Merged PR to Terraform | +8 | `hashicorp/*` |
| Merged PR to Prometheus | +8 | `prometheus/*` |

**Maximum positive**: +30 (capped to prevent gaming)

## Notable Organizations Configuration

```python
NOTABLE_ORGS = {
    # Tier 1: Major foundations (+15)
    "apache": {"score": 15, "name": "Apache Software Foundation"},
    "linuxfoundation": {"score": 15, "name": "Linux Foundation"},

    # Tier 2: Major projects (+12)
    "cncf": {"score": 12, "name": "CNCF"},
    "kubernetes": {"score": 12, "name": "Kubernetes"},
    "mozilla": {"score": 12, "name": "Mozilla"},
    "envoyproxy": {"score": 12, "name": "Envoy Proxy"},

    # Tier 3: Language ecosystems (+10)
    "rust-lang": {"score": 10, "name": "Rust"},
    "python": {"score": 10, "name": "Python"},
    "nodejs": {"score": 10, "name": "Node.js"},
    "golang": {"score": 10, "name": "Go"},

    # Tier 4: Popular frameworks (+8)
    "django": {"score": 8, "name": "Django"},
    "rails": {"score": 8, "name": "Rails"},
    "hashicorp": {"score": 8, "name": "HashiCorp"},
    "prometheus": {"score": 8, "name": "Prometheus"},
    "grafana": {"score": 8, "name": "Grafana"},
    "elastic": {"score": 8, "name": "Elastic"},
}

# Special repos not under org names
NOTABLE_REPOS = {
    "torvalds/linux": {"score": 15, "name": "Linux Kernel"},
    "microsoft/vscode": {"score": 10, "name": "VS Code"},
    "facebook/react": {"score": 10, "name": "React"},
    "vercel/next.js": {"score": 8, "name": "Next.js"},
}
```

## PyGithub API Usage

### Search for Merged PRs to Notable Orgs

```python
from github import Github

def search_merged_prs_to_org(g: Github, username: str, org: str) -> list:
    """
    Search for merged PRs from user to a specific org.

    Query: author:{username} type:pr is:merged org:{org}
    """
    query = f"author:{username} type:pr is:merged org:{org}"
    results = g.search_issues(query, sort="created", order="desc")
    return list(results)


def search_merged_prs_to_repo(g: Github, username: str, repo: str) -> list:
    """
    Search for merged PRs from user to a specific repo.

    Query: author:{username} type:pr is:merged repo:{repo}
    """
    query = f"author:{username} type:pr is:merged repo:{repo}"
    results = g.search_issues(query, sort="created", order="desc")
    return list(results)
```

## Implementation

```python
from dataclasses import dataclass
from github import Github
import structlog

logger = structlog.get_logger()

NOTABLE_ORGS = {
    "apache": {"score": 15, "name": "Apache Software Foundation"},
    "linuxfoundation": {"score": 15, "name": "Linux Foundation"},
    "cncf": {"score": 12, "name": "CNCF"},
    "kubernetes": {"score": 12, "name": "Kubernetes"},
    "mozilla": {"score": 12, "name": "Mozilla"},
    "envoyproxy": {"score": 12, "name": "Envoy Proxy"},
    "rust-lang": {"score": 10, "name": "Rust"},
    "python": {"score": 10, "name": "Python"},
    "nodejs": {"score": 10, "name": "Node.js"},
    "golang": {"score": 10, "name": "Go"},
    "django": {"score": 8, "name": "Django"},
    "rails": {"score": 8, "name": "Rails"},
    "hashicorp": {"score": 8, "name": "HashiCorp"},
    "prometheus": {"score": 8, "name": "Prometheus"},
    "grafana": {"score": 8, "name": "Grafana"},
}

NOTABLE_REPOS = {
    "torvalds/linux": {"score": 15, "name": "Linux Kernel"},
    "microsoft/vscode": {"score": 10, "name": "VS Code"},
    "facebook/react": {"score": 10, "name": "React"},
}

MAX_SCORE = 30  # Cap to prevent gaming


@dataclass
class NotableContribution:
    org_or_repo: str
    name: str
    pr_count: int
    score_contribution: int


@dataclass
class NotableOSSResult:
    score: int
    contributions: list[NotableContribution]
    total_notable_prs: int
    orgs_checked: int


def calculate_notable_oss_contributions(
    g: Github,
    username: str,
) -> NotableOSSResult:
    """
    Calculate score for contributions to notable OSS projects.

    Args:
        g: PyGithub Github instance
        username: GitHub username to analyze

    Returns:
        NotableOSSResult with score and contribution details
    """
    contributions = []
    total_score = 0
    total_prs = 0
    orgs_checked = 0

    # Check notable organizations
    for org, config in NOTABLE_ORGS.items():
        orgs_checked += 1

        try:
            query = f"author:{username} type:pr is:merged org:{org}"
            results = g.search_issues(query)
            pr_count = results.totalCount

            if pr_count > 0:
                total_prs += pr_count
                score_contribution = config["score"]

                contributions.append(NotableContribution(
                    org_or_repo=org,
                    name=config["name"],
                    pr_count=pr_count,
                    score_contribution=score_contribution,
                ))

                total_score += score_contribution
                logger.info(
                    "found_notable_contribution",
                    username=username,
                    org=org,
                    pr_count=pr_count,
                    score=score_contribution,
                )

        except Exception as e:
            logger.warning(
                "notable_org_search_failed",
                username=username,
                org=org,
                error=str(e),
            )

    # Check notable specific repos
    for repo, config in NOTABLE_REPOS.items():
        orgs_checked += 1

        try:
            query = f"author:{username} type:pr is:merged repo:{repo}"
            results = g.search_issues(query)
            pr_count = results.totalCount

            if pr_count > 0:
                total_prs += pr_count
                score_contribution = config["score"]

                contributions.append(NotableContribution(
                    org_or_repo=repo,
                    name=config["name"],
                    pr_count=pr_count,
                    score_contribution=score_contribution,
                ))

                total_score += score_contribution
                logger.info(
                    "found_notable_contribution",
                    username=username,
                    repo=repo,
                    pr_count=pr_count,
                    score=score_contribution,
                )

        except Exception as e:
            logger.warning(
                "notable_repo_search_failed",
                username=username,
                repo=repo,
                error=str(e),
            )

    # Cap the total score
    final_score = min(total_score, MAX_SCORE)

    return NotableOSSResult(
        score=final_score,
        contributions=contributions,
        total_notable_prs=total_prs,
        orgs_checked=orgs_checked,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Search PRs per org | `g.search_issues(query)` | 30/minute (Search API) |

**Total requests**: ~18 searches (15 orgs + 3 repos)

### Rate Limit Concern

With 18 searches per user and a 30/min search limit, this can only process ~1.5 users per minute if running sequentially.

### Optimization Strategies

#### 1. Parallel Search with Rate Limiting

```python
import asyncio
from github import Github
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=25, period=60)  # Stay under 30/min limit
def rate_limited_search(g: Github, query: str):
    return g.search_issues(query)
```

#### 2. Combined Query (Limited)

GitHub search doesn't support OR for orgs, but you can check multiple in fewer queries:

```python
# This WON'T work - GitHub doesn't support OR for org:
# query = f"author:{username} type:pr is:merged (org:apache OR org:kubernetes)"

# Alternative: Use a broader search and filter results
query = f"author:{username} type:pr is:merged"
all_prs = g.search_issues(query)

# Then filter by checking if repo owner is in notable list
for pr in all_prs:
    owner = pr.repository.owner.login
    if owner in NOTABLE_ORGS:
        # Count it
```

#### 3. Prioritized Checking

Check high-value orgs first, stop early if max score reached:

```python
def calculate_notable_oss_optimized(g: Github, username: str) -> NotableOSSResult:
    """Stop checking once max score is reached."""
    total_score = 0
    contributions = []

    # Sort by score descending
    sorted_orgs = sorted(NOTABLE_ORGS.items(), key=lambda x: x[1]["score"], reverse=True)

    for org, config in sorted_orgs:
        if total_score >= MAX_SCORE:
            break  # Already at max, stop checking

        # ... search logic ...

    return NotableOSSResult(score=min(total_score, MAX_SCORE), ...)
```

## Edge Cases

1. **Org renames**: Organizations can be renamed (e.g., `facebook` → `meta`). Keep both names in the list.

2. **Forked repos**: A PR to a fork of `kubernetes/kubernetes` shouldn't count. The search API correctly returns only PRs to the canonical repo.

3. **Transferred repos**: Repos can be transferred between orgs. The search returns current location.

4. **Bot accounts**: Some "merged" PRs might be from bot users (e.g., dependabot). These shouldn't give high scores, but they also aren't spam.

5. **Very old contributions**: A contribution from 2015 still counts. Consider time-weighting in the future.

## Testing Considerations

```python
def test_notable_oss_scoring():
    """Test notable OSS contribution scoring."""

    # Mock user with Apache contribution
    mock_search_results = {
        "apache": 2,  # 2 merged PRs to Apache
        "kubernetes": 0,
        "django": 1,  # 1 merged PR to Django
    }

    result = calculate_with_mock(mock_search_results)
    # Apache: +15, Django: +8 = 23
    assert result.score == 23
    assert len(result.contributions) == 2


def test_score_capping():
    """Test that score is capped at MAX_SCORE."""

    # Mock user with contributions to many orgs
    mock_search_results = {
        "apache": 5,      # +15
        "kubernetes": 3,  # +12
        "python": 2,      # +10
        # Total: 37, should be capped to 30
    }

    result = calculate_with_mock(mock_search_results)
    assert result.score == 30  # Capped
```

## Caching Considerations

Notable OSS contributions change slowly:

```python
# Cache key: f"notable_oss:{username}"
# TTL: 24-48 hours (contributions don't change frequently)
```

## Future Improvements

1. **Dynamic org list**: Fetch trending/popular orgs from GitHub and add to the list.

2. **Contribution recency**: Weight recent contributions higher than old ones.

3. **PR quality analysis**: A merged typo fix shouldn't count the same as a major feature.

4. **Commit contributions**: Some projects accept commits directly (not PRs). Count those too.

5. **Maintainer status**: If the user is a maintainer of a notable project, that's even better than just having PRs merged.
