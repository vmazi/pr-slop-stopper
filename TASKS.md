# PR Slop Stopper - Development Task List

Track implementation progress by checking off completed tasks.

## Legend
- `[ ]` Not started
- `[x]` Completed
- `[~]` In progress
- `[!]` Blocked

---

## Development Practices

**IMPORTANT**: Follow these practices after completing each task to maintain code quality.

### After Every Code Change

Run these commands and ensure they pass before considering a task complete:

```bash
# 1. Lint check
uv run ruff check .

# 2. Format check
uv run ruff format --check .

# 3. Type check
uv run ty check src/

# 4. Run tests
uv run pytest -v

# Or run all at once via build.sh (stops on first failure):
./build.sh
```

### Quality Gates Checklist

Before marking any task as `[x]` Completed:

- [ ] Code passes `uv run ruff check .` (no lint errors)
- [ ] Code passes `uv run ruff format --check .` (properly formatted)
- [ ] Code passes `uv run ty check src/` (no type errors)
- [ ] All tests pass `uv run pytest -v`
- [ ] New code has corresponding tests
- [ ] `./build.sh` completes successfully

### Quick Fix Commands

```bash
# Auto-fix lint issues
uv run ruff check . --fix

# Auto-format code
uv run ruff format .

# Run specific test file
uv run pytest tests/test_heuristics/test_account_age.py -v

# Run tests with coverage
uv run pytest -v --cov=src/pr_slop_stopper
```

### Development Workflow

1. **Start task** - Mark as `[~]` in progress
2. **Write code** - Implement the feature
3. **Write tests** - Add unit tests for new code
4. **Run checks** - Execute all quality gates
5. **Fix issues** - Address any failures
6. **Verify** - Run `./build.sh` end-to-end
7. **Complete** - Mark as `[x]` only when all checks pass

### Test-Driven Development (Recommended)

For heuristics and core logic:
1. Write test first (expected behavior)
2. Run test (should fail)
3. Implement code
4. Run test (should pass)
5. Run all checks

---

## 1. Human Tasks (Manual Steps)

These tasks require manual action outside of code.

### GitHub App Registration

- [ ] Create GitHub App at github.com/settings/apps/new
  - [ ] App name: `PR Slop Stopper` (or similar unique name)
  - [ ] Homepage URL: Your service URL
  - [ ] Webhook URL: `https://<your-domain>/api/webhook/github`
  - [ ] Generate webhook secret and save securely
- [ ] Configure permissions:
  - [ ] Pull requests: Read & Write
  - [ ] Issues: Read & Write (for labels)
  - [ ] Metadata: Read
  - [ ] Members: Read
- [ ] Subscribe to events:
  - [ ] Pull request
- [ ] Generate and download private key (.pem file)
- [ ] Note the App ID
- [ ] Install app on a test repository/organization

### Infrastructure Setup

- [ ] Set up domain/subdomain for webhook endpoint
- [ ] Configure DNS to point to VPS
- [ ] Set up TLS certificate (Let's Encrypt or similar)
- [ ] Create secrets in deployment environment:
  - [ ] `GITHUB_APP_ID`
  - [ ] `GITHUB_PRIVATE_KEY` (contents of .pem)
  - [ ] `GITHUB_WEBHOOK_SECRET`

---

## 2. Project Structure Setup

### Directory Structure

- [ ] Create `src/pr_slop_stopper/` package directory
- [ ] Create `src/pr_slop_stopper/__init__.py`
- [ ] Create `src/pr_slop_stopper/main.py` (FastAPI app)
- [ ] Create `src/pr_slop_stopper/config.py` (Pydantic settings)
- [ ] Create subpackage directories:
  - [ ] `src/pr_slop_stopper/api/`
  - [ ] `src/pr_slop_stopper/core/`
  - [ ] `src/pr_slop_stopper/core/heuristics/`
  - [ ] `src/pr_slop_stopper/github/`
  - [ ] `src/pr_slop_stopper/actions/`
- [ ] Create `tests/` directory structure

### Configuration Files

- [ ] Update `pyproject.toml` with entry points
- [ ] Create `Containerfile` for production image
- [ ] Create `podman-compose.yml` for deployment
- [ ] Create `.env.example` with all required env vars

---

## 3. GitHub API Client

### Setup

- [ ] Create `src/pr_slop_stopper/github/auth.py`
  - [ ] `GithubAppAuth` class for JWT generation
  - [ ] `get_installation_client(installation_id)` function
- [ ] Create `src/pr_slop_stopper/github/client.py`
  - [ ] Wrapper around PyGithub with error handling
  - [ ] Rate limit handling and backoff
- [ ] Create `src/pr_slop_stopper/github/models.py`
  - [ ] Pydantic models for webhook payloads
  - [ ] `PROpenedEvent` model
  - [ ] `UserProfile` model

### Tests

- [ ] Create `tests/test_github/test_auth.py`
- [ ] Create `tests/test_github/test_client.py` (with mocks)

---

## 4. Heuristics (Ordered by Complexity)

Each heuristic needs:
- Implementation in `src/pr_slop_stopper/core/heuristics/`
- Unit tests in `tests/test_heuristics/`
- Result dataclass with score and breakdown

### Base Infrastructure

- [ ] Create `src/pr_slop_stopper/core/heuristics/base.py`
  - [ ] `HeuristicResult` dataclass (score, breakdown, details)
  - [ ] `BaseHeuristic` abstract class
  - [ ] `HeuristicRegistry` for managing all heuristics

### Tier 1: Simple (Profile Data Only - 1 API call)

#### 4.1 Account Age
- [ ] Create `src/pr_slop_stopper/core/heuristics/account_age.py`
  - [ ] Calculate age from `user.created_at`
  - [ ] Apply tier scoring (-20 to +15)
- [ ] Create `tests/test_heuristics/test_account_age.py`
  - [ ] Test all age tiers
  - [ ] Test boundary conditions

#### 4.2 Profile Completeness
- [ ] Create `src/pr_slop_stopper/core/heuristics/profile_completeness.py`
  - [ ] Check avatar_url, bio, company, location, blog, twitter
  - [ ] LinkedIn detection in blog URL
  - [ ] Apply scoring (+23 to -10)
- [ ] Create `tests/test_heuristics/test_profile_completeness.py`
  - [ ] Test complete profile
  - [ ] Test empty profile
  - [ ] Test LinkedIn matching

#### 4.3 Follower Patterns
- [ ] Create `src/pr_slop_stopper/core/heuristics/follower_patterns.py`
  - [ ] Check followers/following counts
  - [ ] Detect follow-spam pattern (high following, low followers)
  - [ ] Apply scoring (+8 to -10)
- [ ] Create `tests/test_heuristics/test_follower_patterns.py`
  - [ ] Test follower tiers
  - [ ] Test spam detection

### Tier 2: Moderate (Search API Required)

#### 4.4 PR Acceptance Rate
- [ ] Create `src/pr_slop_stopper/core/heuristics/pr_acceptance_rate.py`
  - [ ] Search user's PRs from last 12 months
  - [ ] Calculate monthly merge rates
  - [ ] Detect spam months (high volume, low merge rate)
  - [ ] Apply scoring (+10 to -25)
- [ ] Create `tests/test_heuristics/test_pr_acceptance_rate.py`
  - [ ] Test high merge rate
  - [ ] Test spam month detection
  - [ ] Test edge cases (no PRs, all open)

#### 4.5 Contribution Type Patterns
- [ ] Create `src/pr_slop_stopper/core/heuristics/contribution_type.py`
  - [ ] Analyze PR files (code vs docs)
  - [ ] Detect docs-only spam pattern
  - [ ] Detect identical PR patterns
  - [ ] Apply scoring (+5 to -22)
- [ ] Create `tests/test_heuristics/test_contribution_type.py`
  - [ ] Test code contributions
  - [ ] Test docs-only detection

### Tier 3: Complex (Multiple API Calls)

#### 4.6 Activity Patterns
- [ ] Create `src/pr_slop_stopper/core/heuristics/activity_patterns.py`
  - [ ] Analyze user events for consistency
  - [ ] Detect dormancy burst pattern
  - [ ] Check for low-star repo targeting
  - [ ] Check drive-by PR pattern (PRs to un-starred repos)
  - [ ] Apply scoring (+15 to -43)
- [ ] Create `tests/test_heuristics/test_activity_patterns.py`
  - [ ] Test consistent activity
  - [ ] Test dormancy detection
  - [ ] Test low-star targeting

#### 4.7 Notable OSS Contributions
- [ ] Create `src/pr_slop_stopper/core/heuristics/notable_oss.py`
  - [ ] Define notable orgs list (Apache, Linux, CNCF, etc.)
  - [ ] Search for merged PRs to notable orgs
  - [ ] Apply scoring (0 to +30, capped)
- [ ] Create `tests/test_heuristics/test_notable_oss.py`
  - [ ] Test notable org detection
  - [ ] Test score capping

### Per-PR Check (Context-Specific)

#### 4.8 Fork Timing Check
- [ ] Create `src/pr_slop_stopper/core/heuristics/fork_timing.py`
  - [ ] Compare fork creation time to PR creation time
  - [ ] Flag if fork created <24h before PR
  - [ ] Apply scoring (0 to -10)
- [ ] Create `tests/test_heuristics/test_fork_timing.py`
  - [ ] Test quick fork detection
  - [ ] Test normal fork timing

---

## 5. Scoring Engine

### Implementation

- [ ] Create `src/pr_slop_stopper/core/scorer.py`
  - [ ] `ReputationScorer` class
  - [ ] `calculate_score(user, pr_context)` method
  - [ ] Aggregate all heuristic results
  - [ ] Clamp final score to [-100, +100]
  - [ ] Return detailed breakdown
- [ ] Create `src/pr_slop_stopper/core/models.py`
  - [ ] `ScoringResult` dataclass
  - [ ] `ScoringConfig` from repo config

### Tests

- [ ] Create `tests/test_core/test_scorer.py`
  - [ ] Test score aggregation
  - [ ] Test clamping
  - [ ] Test with subset of heuristics enabled

---

## 6. Webhook Handler

### Implementation

- [ ] Create `src/pr_slop_stopper/api/webhook.py`
  - [ ] `POST /api/webhook/github` endpoint
  - [ ] Signature verification (X-Hub-Signature-256)
  - [ ] Parse `pull_request.opened` events
  - [ ] Background task for scoring (FastAPI BackgroundTasks)
  - [ ] Return 202 Accepted immediately
- [ ] Create `src/pr_slop_stopper/api/health.py`
  - [ ] `GET /health` endpoint
  - [ ] `GET /health/ready` endpoint

### Skip Logic

- [ ] Implement skip conditions:
  - [ ] User is repo collaborator/maintainer
  - [ ] User has previously merged PR to this repo
  - [ ] User is in whitelist (from repo config)

### Tests

- [ ] Create `tests/test_api/test_webhook.py`
  - [ ] Test signature validation
  - [ ] Test event parsing
  - [ ] Test skip conditions
- [ ] Create `tests/test_api/test_health.py`

---

## 7. Actions (Label & Comment)

### Implementation

- [ ] Create `src/pr_slop_stopper/actions/labeler.py`
  - [ ] Create labels if they don't exist
  - [ ] `pr-slop-stopper: warning` label
  - [ ] `pr-slop-stopper: likely-spam` label
  - [ ] Apply label to PR
- [ ] Create `src/pr_slop_stopper/actions/commenter.py`
  - [ ] Generate comment with score breakdown
  - [ ] Include which heuristics contributed
  - [ ] Add link to documentation
  - [ ] Post comment to PR
- [ ] Create `src/pr_slop_stopper/actions/closer.py`
  - [ ] Close PR (for spam threshold)

### Action Orchestration

- [ ] Create `src/pr_slop_stopper/actions/executor.py`
  - [ ] `execute_action(score, config, pr)` function
  - [ ] Determine action based on thresholds
  - [ ] Execute label + comment + optional close

### Tests

- [ ] Create `tests/test_actions/test_labeler.py`
- [ ] Create `tests/test_actions/test_commenter.py`
- [ ] Create `tests/test_actions/test_executor.py`

---

## 8. Configuration

### Repo Config Loading

- [ ] Create `src/pr_slop_stopper/config.py`
  - [ ] `Settings` class (Pydantic BaseSettings)
  - [ ] Load from environment variables
- [ ] Create `src/pr_slop_stopper/core/repo_config.py`
  - [ ] `RepoConfig` model for `.github/pr-slop-stopper.yml`
  - [ ] Default thresholds (warn: -10, close: -40)
  - [ ] Whitelist parsing
  - [ ] Heuristic enable/disable flags
  - [ ] Fetch config from repo via GitHub API

### Tests

- [ ] Create `tests/test_config.py`
  - [ ] Test default values
  - [ ] Test config parsing
  - [ ] Test invalid config handling

---

## 9. Testing Infrastructure

### pytest Setup

- [ ] Configure `pyproject.toml` pytest settings
- [ ] Create `tests/conftest.py`
  - [ ] Mock GitHub client fixture
  - [ ] Sample user data fixtures
  - [ ] Sample PR event fixtures

### Integration Tests

- [ ] Create `tests/integration/test_full_flow.py`
  - [ ] Test complete webhook → score → action flow
  - [ ] Mock GitHub API responses

### Test Data

- [ ] Create `tests/fixtures/` directory
  - [ ] Sample webhook payloads
  - [ ] Sample user profiles (good, suspicious, spam)
  - [ ] Sample PR data

---

## 10. CI/CD

### GitHub Actions

- [ ] Create `.github/workflows/ci.yml`
  - [ ] Trigger on push and PR to main
  - [ ] Set up Python 3.11 with uv
  - [ ] Run `uv sync --dev`
  - [ ] Run `uv run ruff check .`
  - [ ] Run `uv run ruff format --check .`
  - [ ] Run `uv run ty check src/`
  - [ ] Run `uv run pytest -v`

---

## 11. Deployment

### Container Image

- [ ] Create `Containerfile`
  - [ ] Base image: `python:3.11-slim`
  - [ ] Install uv
  - [ ] Copy project files
  - [ ] Install dependencies
  - [ ] Expose port 8000
  - [ ] CMD: uvicorn

### Podman Compose

- [ ] Create `podman-compose.yml`
  - [ ] `pr-slop-stopper` service
  - [ ] Environment variables from `.env`
  - [ ] Health checks
  - [ ] Port mapping

### Deployment Files

- [ ] Create `.env.example`
- [ ] Create `devenv.sh` for local development

---

## 12. Documentation Updates

- [ ] Update `README.md` with:
  - [ ] Installation instructions
  - [ ] Configuration guide
  - [ ] Local development setup
- [ ] Create `CONTRIBUTING.md`
- [ ] Create `CHANGELOG.md`

---

## Deferred: Database Layer (Future Phase)

These tasks are deferred until needed for caching/dashboard features.

### When to Add
- Performance optimization (score caching with 24h TTL)
- Dashboard feature (historical query needs)
- Organization-wide whitelist management
- Analytics/metrics storage

### Deferred Tasks

- [ ] Add `pgserver` to dev dependencies
- [ ] Add `asyncpg`, `sqlalchemy[asyncio]` to dependencies
- [ ] Create `src/pr_slop_stopper/db/` package
- [ ] Create database models:
  - [ ] `UserScore` (cache)
  - [ ] `PRAnalysisLog` (audit)
  - [ ] `Installation` (config cache)
  - [ ] `Whitelist` (org-wide)
- [ ] Set up Alembic migrations
- [ ] Create CRUD operations
- [ ] Add postgres service to podman-compose.yml
- [ ] Integration tests with pgserver

---

## Implementation Order (Suggested)

### Phase 1: Foundation
1. Project structure setup
2. Configuration (Settings class)
3. GitHub API client & auth

### Phase 2: Simple Heuristics + Scoring
4. Base heuristic infrastructure
5. Account age heuristic
6. Profile completeness heuristic
7. Follower patterns heuristic
8. Scoring engine (aggregate results)

### Phase 3: Webhook & Actions
9. Webhook handler with signature verification
10. Repo config loading
11. Skip logic (maintainer, whitelist)
12. Labeler and commenter
13. Action executor

### Phase 4: Integration & CI
14. Integration tests
15. CI/CD pipeline
16. Containerfile & podman-compose

### Phase 5: Complex Heuristics
17. PR acceptance rate
18. Contribution type patterns
19. Activity patterns
20. Notable OSS contributions
21. Fork timing check (per-PR)

### Phase 6: Deploy & Document
22. Documentation updates
23. GitHub App registration (human task)
24. Deploy to VPS

---

## Progress Summary

| Category | Total | Done | Progress |
|----------|-------|------|----------|
| Human Tasks | 11 | 0 | 0% |
| Project Setup | 10 | 0 | 0% |
| GitHub Client | 6 | 0 | 0% |
| Heuristics | 24 | 0 | 0% |
| Scoring Engine | 4 | 0 | 0% |
| Webhook | 7 | 0 | 0% |
| Actions | 8 | 0 | 0% |
| Configuration | 4 | 0 | 0% |
| Testing | 5 | 0 | 0% |
| CI/CD | 1 | 0 | 0% |
| Deployment | 4 | 0 | 0% |
| Documentation | 3 | 0 | 0% |
| **Total** | **87** | **0** | **0%** |

*Database tasks (13) deferred to future phase*
