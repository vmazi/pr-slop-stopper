# Architecture Document

## System Overview

PR Slop Stopper is deployed as a GitHub App with a FastAPI backend service hosted on a Podman-enabled VPS.

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub                                   │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────────────────┐  │
│  │  Repo   │───▶│ PR Open │───▶│  Webhook: pull_request.opened│  │
│  └─────────┘    └─────────┘    └──────────────┬──────────────┘  │
└───────────────────────────────────────────────┼─────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VPS (Podman)                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    pr-slop-stopper                           │   │
│  │  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐   │   │
│  │  │   FastAPI   │──▶│  Scorer      │──▶│  PostgreSQL  │   │   │
│  │  │  (webhook)  │   │  Engine      │   │  (cache/log) │   │   │
│  │  └──────┬──────┘   └──────────────┘   └──────────────┘   │   │
│  │         │                                                 │   │
│  │         ▼                                                 │   │
│  │  ┌─────────────┐                                         │   │
│  │  │  GitHub API │ (fetch profile, PR history, etc.)       │   │
│  │  └─────────────┘                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Authentik                              │   │
│  │              (OIDC for future dashboard)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## GitHub App Setup

### Creating a GitHub App

1. Go to **GitHub Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**

2. **Basic Information**:
   - App name: `PR Slop Stopper`
   - Homepage URL: Your service URL
   - Description: Automatic spam PR detection using reputation scoring

3. **Webhook Configuration**:
   - Webhook URL: `https://your-domain.com/api/webhook/github`
   - Webhook secret: Generate a secure random string
   - Active: ✓

4. **Permissions Required**:

   | Permission | Access | Reason |
   |------------|--------|--------|
   | Pull requests | Read & Write | Read PR details, add labels/comments, close PRs |
   | Issues | Read & Write | Create labels |
   | Metadata | Read | Access repo metadata |
   | Members | Read | Check if user is maintainer/collaborator |

5. **Subscribe to Events**:
   - Pull request

6. **Installation**:
   - Allow installation on: Any account (or specific accounts)
   - Generate and download private key

### App Authentication

GitHub Apps authenticate using JWT tokens:

```python
import jwt
import time
import httpx

def generate_jwt(app_id: str, private_key: str) -> str:
    """Generate a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds ago
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")

async def get_installation_token(jwt_token: str, installation_id: int) -> str:
    """Exchange JWT for installation access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        return response.json()["token"]
```

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| API Framework | FastAPI | Async support, auto OpenAPI docs, Pydantic validation |
| GitHub API Client | PyGithub | Mature Python library for GitHub REST API |
| Database | PostgreSQL | Reliable, good for caching and logging |
| ORM | SQLAlchemy 2.0 | Async support, mature ecosystem |
| Task Queue | None (v1) | Synchronous processing initially |
| Auth (future) | Authentik OIDC | Existing infrastructure for dashboard |
| Container | Podman | Existing VPS infrastructure |
| Reverse Proxy | Existing infra | TLS termination, routing |

## GitHub API Client (PyGithub)

We use [PyGithub](https://github.com/PyGithub/PyGithub) for all GitHub API interactions. This provides a typed, Pythonic interface to the GitHub REST API.

### Installation

```bash
pip install PyGithub
```

### Authentication with GitHub App

```python
from github import Github, GithubIntegration

def get_github_client(app_id: int, private_key: str, installation_id: int) -> Github:
    """
    Create authenticated GitHub client for an installation.

    Uses GitHub App authentication flow:
    1. Generate JWT from app credentials
    2. Exchange JWT for installation access token
    3. Create Github client with installation token
    """
    integration = GithubIntegration(app_id, private_key)
    access_token = integration.get_access_token(installation_id).token
    return Github(access_token)
```

### Key Objects Used

| Object | PyGithub Class | Use Case |
|--------|---------------|----------|
| User Profile | `NamedUser` | Profile completeness, account age, followers |
| Pull Request | `PullRequest` | PR analysis, merge status, files changed |
| Repository | `Repository` | Star count, fork detection, collaborators |
| Issue (Search) | `Issue` | Search results for PRs (PRs are issues) |

### User Profile Fields

```python
user = g.get_user("username")

# Profile fields
user.avatar_url      # str: Profile picture URL
user.bio             # str | None: Bio text
user.blog            # str | None: Website URL
user.company         # str | None: Company name
user.location        # str | None: Location
user.twitter_username # str | None: Twitter handle
user.name            # str | None: Display name
user.email           # str | None: Public email

# Metrics
user.followers       # int: Follower count
user.following       # int: Following count
user.public_repos    # int: Public repository count

# Timestamps
user.created_at      # datetime: Account creation date
user.updated_at      # datetime: Last profile update
```

### Search API Usage

```python
# Search for user's PRs
query = "author:username type:pr created:>=2024-01-01"
results = g.search_issues(query, sort="created", order="desc")

# Search for merged PRs to specific org
query = "author:username type:pr is:merged org:kubernetes"
results = g.search_issues(query)

# Access search result properties
for issue in results:
    issue.number        # PR number
    issue.state         # "open" or "closed"
    issue.created_at    # Creation timestamp
    issue.repository    # Repository object
```

### Rate Limiting

| API Type | Limit | Notes |
|----------|-------|-------|
| Core API | 5,000/hour per installation | Most operations |
| Search API | 30/minute | Shared across all search queries |
| GraphQL | 5,000 points/hour | Alternative for complex queries |

```python
# Check rate limit status
rate_limit = g.get_rate_limit()
print(f"Core: {rate_limit.core.remaining}/{rate_limit.core.limit}")
print(f"Search: {rate_limit.search.remaining}/{rate_limit.search.limit}")
```

### Heuristic Implementation Details

Detailed implementation documentation for each heuristic:

| Heuristic | Documentation |
|-----------|---------------|
| Profile Completeness | [profile_completeness_implementation_details.md](heuristics/profile_completeness_implementation_details.md) |
| Account Age | [account_age_implementation_details.md](heuristics/account_age_implementation_details.md) |
| PR Acceptance Rate | [pr_acceptance_rate_implementation_details.md](heuristics/pr_acceptance_rate_implementation_details.md) |
| Notable OSS Contributions | [notable_oss_contributions_implementation_details.md](heuristics/notable_oss_contributions_implementation_details.md) |
| Activity Patterns | [activity_patterns_implementation_details.md](heuristics/activity_patterns_implementation_details.md) |
| Follower Patterns | [follower_patterns_implementation_details.md](heuristics/follower_patterns_implementation_details.md) |
| Contribution Type Patterns | [contribution_type_patterns_implementation_details.md](heuristics/contribution_type_patterns_implementation_details.md) |

## Project Structure

```
pr-slop-stopper/
├── docs/
│   ├── PRD.md
│   ├── HEURISTICS.md
│   └── ARCHITECTURE.md
├── src/
│   └── pr_slop_stopper/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Settings management
│       ├── api/
│       │   ├── __init__.py
│       │   ├── webhook.py       # GitHub webhook handler
│       │   └── health.py        # Health check endpoints
│       ├── core/
│       │   ├── __init__.py
│       │   ├── scorer.py        # Main scoring engine
│       │   └── heuristics/      # Individual heuristic implementations
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── profile.py
│       │       ├── account_age.py
│       │       ├── pr_history.py
│       │       ├── notable_oss.py
│       │       ├── activity.py
│       │       ├── followers.py
│       │       └── contribution_type.py
│       ├── github/
│       │   ├── __init__.py
│       │   ├── client.py        # GitHub API client
│       │   ├── auth.py          # App authentication
│       │   └── models.py        # Pydantic models for API responses
│       ├── db/
│       │   ├── __init__.py
│       │   ├── database.py      # Database connection
│       │   ├── models.py        # SQLAlchemy models
│       │   └── crud.py          # Database operations
│       └── actions/
│           ├── __init__.py
│           ├── labeler.py       # Apply labels to PRs
│           └── commenter.py     # Add comments to PRs
├── tests/
│   ├── conftest.py
│   ├── test_scorer.py
│   ├── test_heuristics/
│   └── test_webhook.py
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── Containerfile
├── build.sh
├── devenv.sh
└── README.md
```

## Database Schema

```sql
-- Cached user reputation scores
CREATE TABLE user_scores (
    id SERIAL PRIMARY KEY,
    github_user_id BIGINT UNIQUE NOT NULL,
    github_username VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL,
    score_breakdown JSONB NOT NULL,  -- Detailed heuristic scores
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_scores_github_user_id ON user_scores(github_user_id);
CREATE INDEX idx_user_scores_expires_at ON user_scores(expires_at);

-- Installation configuration cache
CREATE TABLE installations (
    id SERIAL PRIMARY KEY,
    installation_id BIGINT UNIQUE NOT NULL,
    account_type VARCHAR(50) NOT NULL,  -- 'User' or 'Organization'
    account_login VARCHAR(255) NOT NULL,
    config JSONB,  -- Cached repo config
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log of all PR analyses
CREATE TABLE pr_analysis_log (
    id SERIAL PRIMARY KEY,
    installation_id BIGINT NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_author_id BIGINT NOT NULL,
    pr_author_login VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL,
    action_taken VARCHAR(50) NOT NULL,  -- 'none', 'warn', 'close'
    score_breakdown JSONB NOT NULL,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pr_analysis_log_repo ON pr_analysis_log(repo_full_name);
CREATE INDEX idx_pr_analysis_log_author ON pr_analysis_log(pr_author_login);

-- Whitelist entries (org-level, future)
CREATE TABLE whitelists (
    id SERIAL PRIMARY KEY,
    installation_id BIGINT NOT NULL,
    github_username VARCHAR(255) NOT NULL,
    added_by VARCHAR(255) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(installation_id, github_username)
);
```

## API Endpoints

### Webhook Endpoint

```
POST /api/webhook/github
```

Receives GitHub webhook events. Validates signature using webhook secret.

**Important**: GitHub expects webhook responses within 10 seconds. To prevent timeouts, we use [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) to process the scoring asynchronously after returning an immediate `202 Accepted` response.

**Synchronous Flow** (must complete quickly):
1. Validate webhook signature
2. Parse event type
3. Return `202 Accepted` immediately
4. Queue scoring task in background

**Background Task Flow** (runs after response):
1. Check if PR author should be analyzed
2. Fetch/calculate reputation score
3. Take action based on thresholds
4. Log result

#### Webhook Handler Implementation

```python
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import structlog

router = APIRouter()
logger = structlog.get_logger()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_pr_opened(
    installation_id: int,
    repo_full_name: str,
    pr_number: int,
    pr_author: str,
):
    """
    Background task to process a PR opened event.

    This runs AFTER the webhook response is sent to GitHub.
    """
    logger.info(
        "processing_pr",
        repo=repo_full_name,
        pr=pr_number,
        author=pr_author,
    )

    try:
        # 1. Check skip conditions (maintainer, whitelisted, etc.)
        # 2. Get or calculate user reputation score
        # 3. Apply labels/comments based on thresholds
        # 4. Log the result
        pass
    except Exception as e:
        logger.error(
            "pr_processing_failed",
            repo=repo_full_name,
            pr=pr_number,
            error=str(e),
        )


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle GitHub webhook events.

    Returns 202 Accepted immediately, processes in background.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    # Only process pull_request.opened events
    if event_type != "pull_request":
        return JSONResponse(
            status_code=200,
            content={"status": "ignored", "reason": "not a PR event"}
        )

    action = payload.get("action")
    if action != "opened":
        return JSONResponse(
            status_code=200,
            content={"status": "ignored", "reason": f"action={action}"}
        )

    # Extract PR details
    installation_id = payload["installation"]["id"]
    repo_full_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    pr_author = payload["pull_request"]["user"]["login"]

    # Queue background task - this runs AFTER response is sent
    background_tasks.add_task(
        process_pr_opened,
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        pr_author=pr_author,
    )

    # Return immediately - GitHub gets fast response
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "PR analysis queued",
            "pr": f"{repo_full_name}#{pr_number}",
        }
    )
```

#### When to Use BackgroundTasks vs. Celery

| Use Case | Solution |
|----------|----------|
| Simple webhook processing | FastAPI `BackgroundTasks` |
| Email notifications | FastAPI `BackgroundTasks` |
| Heavy computation (ML scoring) | Celery + Redis |
| High-volume processing | Celery + Redis |
| Distributed workers | Celery + Redis |

For v1, `BackgroundTasks` is sufficient. If we need to scale to high volumes or add ML-based scoring, we should migrate to Celery.

### Health Endpoints

```
GET /health          # Basic health check
GET /health/ready    # Readiness (DB connected)
```

### Future: Dashboard API

```
GET  /api/installations           # List installations
GET  /api/installations/:id/stats # Get statistics
POST /api/installations/:id/whitelist  # Add to whitelist
```

## Webhook Processing Flow

```
┌────────────────┐
│ Webhook Event  │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Validate       │───No──▶ 401 Unauthorized
│ Signature      │
└───────┬────────┘
        │ Yes
        ▼
┌────────────────┐
│ Parse Event    │
│ (PR opened?)   │───No──▶ 200 OK (ignore)
└───────┬────────┘
        │ Yes
        ▼
┌────────────────┐
│ Check Skip     │
│ Conditions     │───Yes─▶ 200 OK (skip)
│ - Maintainer?  │         Log: "Skipped: maintainer"
│ - Whitelisted? │
│ - Has merged?  │
└───────┬────────┘
        │ No
        ▼
┌────────────────┐
│ Check Cache    │───Hit──▶ Use cached score
│ for User Score │
└───────┬────────┘
        │ Miss
        ▼
┌────────────────┐
│ Fetch User     │
│ Profile Data   │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Run Heuristics │
│ Calculate Score│
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Cache Score    │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Load Repo      │
│ Config         │
└───────┬────────┘
        │
        ▼
┌────────────────┐        ┌────────────────┐
│ Score >= warn? │───Yes─▶│ No action      │
└───────┬────────┘        └────────────────┘
        │ No
        ▼
┌────────────────┐        ┌────────────────┐
│ Score >= close?│───Yes─▶│ Add warn label │
└───────┬────────┘        │ + comment      │
        │ No              └────────────────┘
        ▼
┌────────────────┐
│ Add spam label │
│ + comment      │
│ + close PR     │
└────────────────┘
```

## Configuration Management

Repository configuration is read from `.github/pr-slop-stopper.yml`:

```python
from pydantic import BaseModel
from typing import Optional

class Thresholds(BaseModel):
    warn: int = -10
    close: int = -40

class HeuristicConfig(BaseModel):
    profile_completeness: bool = True
    account_age: bool = True
    pr_acceptance_rate: bool = True
    notable_contributions: bool = True
    activity_patterns: bool = True
    follower_patterns: bool = True
    contribution_type: bool = True

class RepoConfig(BaseModel):
    thresholds: Thresholds = Thresholds()
    whitelist: list[str] = []
    heuristics: HeuristicConfig = HeuristicConfig()
```

## Deployment

### Container Build

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install uv && uv pip install --system -e .

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "pr_slop_stopper.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
# GitHub App
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/secrets/github-app.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pr_slop_stopper

# Optional
LOG_LEVEL=INFO
SCORE_CACHE_TTL_HOURS=24
```

### Podman Compose

```yaml
version: "3.8"

services:
  pr-slop-stopper:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://prss:prss@db:5432/pr_slop_stopper
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
    volumes:
      - ./secrets:/secrets:ro
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=prss
      - POSTGRES_PASSWORD=prss
      - POSTGRES_DB=pr_slop_stopper
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Rate Limiting & Caching

### GitHub API Rate Limits

- **Authenticated requests**: 5,000/hour per installation
- **Search API**: 30 requests/minute

**Mitigation strategies**:
1. Cache user scores (24h TTL default)
2. Batch profile data requests where possible
3. Graceful degradation if rate limited

### Caching Strategy

```python
async def get_user_score(user_id: int) -> Optional[CachedScore]:
    """Check cache before calculating."""
    cached = await db.get_cached_score(user_id)
    if cached and cached.expires_at > datetime.utcnow():
        return cached
    return None

async def cache_user_score(user_id: int, score: int, breakdown: dict):
    """Cache score with TTL."""
    await db.upsert_score(
        user_id=user_id,
        score=score,
        breakdown=breakdown,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
```

## Security Considerations

1. **Webhook signature validation** - Always verify `X-Hub-Signature-256`
2. **Private key protection** - Store in secrets manager, mount read-only
3. **Minimal permissions** - Only request necessary GitHub permissions
4. **Input validation** - Pydantic models for all external input
5. **SQL injection prevention** - SQLAlchemy parameterized queries
6. **Rate limiting** - Protect against DoS on public endpoints

## Monitoring & Observability

### Logging

Use `structlog` for structured JSON logging:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "pr_analyzed",
    repo=repo_full_name,
    pr_number=pr_number,
    author=author_login,
    score=score,
    action=action_taken,
)
```

### Metrics (Future)

Expose Prometheus metrics:
- `pr_slop_stopper_prs_analyzed_total`
- `pr_slop_stopper_prs_flagged_total{action="warn|close"}`
- `pr_slop_stopper_score_calculation_seconds`
- `pr_slop_stopper_github_api_requests_total`

## Future Enhancements

1. **Async task queue** - Move scoring to background workers for resilience
2. **Redis cache** - Replace/supplement PostgreSQL cache for performance
3. **Distributed processing** - Handle high-volume organizations
4. **ML-based scoring** - Supplement heuristics with trained models
5. **Dashboard** - React frontend authenticated via Authentik OIDC

## References

- [Creating GitHub Apps](https://docs.github.com/en/apps/creating-github-apps) - Official GitHub documentation
- [Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
- [About authentication with a GitHub App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app)
- [Building a GitHub App that responds to webhook events](https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-github-app-that-responds-to-webhook-events)
