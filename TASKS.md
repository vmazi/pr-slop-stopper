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

- [x] Create `src/pr_slop_stopper/` package directory
- [x] Create `src/pr_slop_stopper/__init__.py`
- [x] Create `src/pr_slop_stopper/main.py` (FastAPI app)
- [x] Create `src/pr_slop_stopper/config.py` (Pydantic settings)
- [x] Create subpackage directories:
  - [x] `src/pr_slop_stopper/api/`
  - [x] `src/pr_slop_stopper/core/`
  - [x] `src/pr_slop_stopper/core/heuristics/`
  - [x] `src/pr_slop_stopper/github/`
  - [x] `src/pr_slop_stopper/actions/`
- [x] Create `tests/` directory structure

### Configuration Files

- [x] Update `pyproject.toml` with entry points
- [ ] Create `Containerfile` for production image
- [ ] Create `podman-compose.yml` for deployment
- [ ] Create `.env.example` with all required env vars

---

## 3. GitHub API Client

### Setup

- [x] Create `src/pr_slop_stopper/github/auth.py`
  - [x] `GithubAppAuth` class for JWT generation
  - [x] `get_installation_client(installation_id)` function
- [x] Create `src/pr_slop_stopper/github/client.py`
  - [x] Wrapper around PyGithub with error handling
  - [ ] Rate limit handling and backoff
- [x] Create `src/pr_slop_stopper/github/models.py`
  - [x] Pydantic models for webhook payloads
  - [x] `PROpenedEvent` model
  - [x] `UserProfile` model

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

- [x] Create `src/pr_slop_stopper/core/heuristics/base.py`
  - [x] `HeuristicResult` dataclass (score, breakdown, details)
  - [x] `BaseHeuristic` abstract class
  - [x] `HeuristicRegistry` for managing all heuristics

### Tier 1: Simple (Profile Data Only - 1 API call)

#### 4.1 Account Age
- [x] Create `src/pr_slop_stopper/core/heuristics/account_age.py`
  - [x] Calculate age from `user.created_at`
  - [x] Apply tier scoring (-20 to +15)
- [x] Create `tests/test_heuristics/test_account_age.py`
  - [x] Test all age tiers
  - [x] Test boundary conditions

#### 4.2 Profile Completeness
- [x] Create `src/pr_slop_stopper/core/heuristics/profile_completeness.py`
  - [x] Check avatar_url, bio, company, location, blog, twitter
  - [x] LinkedIn detection in blog URL
  - [x] Apply scoring (+23 to -10)
- [x] Create `tests/test_heuristics/test_profile_completeness.py`
  - [x] Test complete profile
  - [x] Test empty profile
  - [x] Test LinkedIn matching

#### 4.3 Follower Patterns
- [x] Create `src/pr_slop_stopper/core/heuristics/follower_patterns.py`
  - [x] Check followers/following counts
  - [x] Detect follow-spam pattern (high following, low followers)
  - [x] Apply scoring (+8 to -10)
- [x] Create `tests/test_heuristics/test_follower_patterns.py`
  - [x] Test follower tiers
  - [x] Test spam detection

### Tier 2: Moderate (Search API Required)

#### 4.4 PR Acceptance Rate
- [x] Create `src/pr_slop_stopper/core/heuristics/pr_acceptance_rate.py`
  - [x] Search user's PRs from last 12 months
  - [x] Calculate monthly merge rates
  - [x] Detect spam months (high volume, low merge rate)
  - [x] Apply scoring (+10 to -25)
- [x] Create `tests/test_heuristics/test_pr_acceptance_rate.py`
  - [x] Test high merge rate
  - [x] Test spam month detection
  - [x] Test edge cases (no PRs, all open)

#### 4.5 Contribution Type Patterns
- [x] Create `src/pr_slop_stopper/core/heuristics/contribution_type.py`
  - [x] Analyze PR files (code vs docs)
  - [x] Detect docs-only spam pattern
  - [x] Detect trivial PR patterns
  - [x] Apply scoring (+10 to -15)
- [x] Create `tests/test_heuristics/test_contribution_type.py`
  - [x] Test code contributions
  - [x] Test docs-only detection

### Tier 3: Complex (Multiple API Calls)

#### 4.6 Activity Patterns
- [x] Create `src/pr_slop_stopper/core/heuristics/activity_patterns.py`
  - [x] Analyze user events for consistency
  - [x] Detect dormancy burst pattern
  - [x] Detect burst activity in single month
  - [x] Detect suspicious timing patterns
  - [x] Apply scoring (+10 to -20)
- [x] Create `tests/test_heuristics/test_activity_patterns.py`
  - [x] Test consistent activity
  - [x] Test dormancy detection
  - [x] Test burst detection

#### 4.7 Notable OSS Contributions
- [x] Create `src/pr_slop_stopper/core/heuristics/notable_contributions.py`
  - [x] Classify repos by star count (very popular, popular, notable, small)
  - [x] Search for merged PRs to notable repos
  - [x] Apply scoring (+20 to -10)
- [x] Create `tests/test_heuristics/test_notable_contributions.py`
  - [x] Test notable repo detection
  - [x] Test score calculation

### Per-PR Check (Context-Specific)

#### 4.8 Fork Timing Check
- [x] Create `src/pr_slop_stopper/core/heuristics/fork_timing.py`
  - [x] Compare fork creation time to PR creation time
  - [x] Flag instant fork-to-PR pattern (<1 hour)
  - [x] Flag quick fork-to-PR pattern (<24 hours)
  - [x] Apply scoring (+10 to -20)
- [x] Create `tests/test_heuristics/test_fork_timing.py`
  - [x] Test quick fork detection
  - [x] Test established contributor detection

---

## 5. Scoring Engine

### Implementation

- [x] Create `src/pr_slop_stopper/core/scorer.py`
  - [x] `ReputationScorer` class
  - [x] `calculate_score(user, pr_context)` method
  - [x] Aggregate all heuristic results
  - [x] Clamp final score to [-100, +100]
  - [x] Return detailed breakdown
- [x] Create `src/pr_slop_stopper/core/models.py`
  - [x] `ScoringResult` dataclass
  - [x] `ScoringConfig` from repo config

### Tests

- [x] Create `tests/test_core/test_scorer.py`
  - [x] Test score aggregation
  - [x] Test clamping
  - [x] Test with subset of heuristics enabled

---

## 6. Webhook Handler

### Implementation

- [x] Create `src/pr_slop_stopper/api/webhook.py`
  - [x] `POST /api/webhook/github` endpoint
  - [x] Signature verification (X-Hub-Signature-256)
  - [x] Parse `pull_request.opened` events
  - [x] Background task for scoring (FastAPI BackgroundTasks)
  - [x] Return 202 Accepted immediately
- [x] Create `src/pr_slop_stopper/api/health.py`
  - [x] `GET /health` endpoint
  - [x] `GET /health/ready` endpoint

### Skip Logic

- [x] Implement skip conditions:
  - [x] User is repo collaborator/maintainer
  - [x] User has previously merged PR to this repo
  - [x] User is in whitelist (from repo config)

### Tests

- [x] Create `tests/test_api/test_webhook.py`
  - [x] Test signature validation
  - [x] Test event parsing
  - [ ] Test skip conditions
- [x] Create `tests/test_api/test_health.py`

---

## 7. Actions (Label & Comment)

### Implementation

- [x] Create `src/pr_slop_stopper/actions/labeler.py`
  - [x] Create labels if they don't exist
  - [x] `pr-slop-stopper: warning` label
  - [x] `pr-slop-stopper: likely-spam` label
  - [x] Apply label to PR
- [x] Create `src/pr_slop_stopper/actions/commenter.py`
  - [x] Generate comment with score breakdown
  - [x] Include which heuristics contributed
  - [x] Add link to documentation
  - [x] Post comment to PR
- [x] Create `src/pr_slop_stopper/actions/closer.py`
  - [x] Close PR (for spam threshold)

### Action Orchestration

- [x] Create `src/pr_slop_stopper/actions/executor.py`
  - [x] `execute_action(score, config, pr)` function
  - [x] Determine action based on thresholds
  - [x] Execute label + comment + optional close

### Tests

- [ ] Create `tests/test_actions/test_labeler.py`
- [x] Create `tests/test_actions/test_commenter.py`
- [x] Create `tests/test_actions/test_executor.py`

---

## 8. Configuration

### Repo Config Loading

- [x] Create `src/pr_slop_stopper/config.py`
  - [x] `Settings` class (Pydantic BaseSettings)
  - [x] Load from environment variables
- [x] Create `src/pr_slop_stopper/core/repo_config.py`
  - [x] `RepoConfig` model for `.github/pr-slop-stopper.yml`
  - [x] Default thresholds (warn: -10, close: -40)
  - [x] Whitelist parsing
  - [x] Heuristic enable/disable flags
  - [x] Fetch config from repo via GitHub API

### Tests

- [x] Create `tests/test_config.py`
  - [x] Test default values
  - [x] Test config parsing
  - [x] Test invalid config handling

---

## 9. Testing Infrastructure

### pytest Setup

- [x] Configure `pyproject.toml` pytest settings
- [x] Create `tests/conftest.py`
  - [x] Mock GitHub client fixture
  - [x] Sample user data fixtures
  - [x] Sample PR event fixtures

### Integration Tests

- [x] Create `tests/integration/test_full_flow.py`
  - [x] Test complete webhook → score → action flow
  - [x] Mock GitHub API responses

### Test Data

- [x] Create `tests/fixtures/` directory
  - [x] Sample webhook payloads
  - [x] Sample user profiles (good, suspicious, spam)
  - [x] Sample PR data

---

## 10. CI/CD

### GitHub Actions

- [x] Create `.github/workflows/ci.yml`
  - [x] Trigger on push and PR to main
  - [x] Set up Python 3.11 with uv
  - [x] Run `uv sync --dev`
  - [x] Run `uv run ruff check .`
  - [x] Run `uv run ruff format --check .`
  - [x] Run `uv run ty check src/`
  - [x] Run `uv run pytest -v`

---

## 11. Deployment

### Container Image

- [x] Create `Containerfile`
  - [x] Base image: `python:3.11-slim`
  - [x] Install uv
  - [x] Copy project files
  - [x] Install dependencies
  - [x] Expose port 8000
  - [x] CMD: uvicorn

### Podman Compose

- [x] Create `podman-compose.yml`
  - [x] `pr-slop-stopper` service
  - [x] Environment variables from `.env`
  - [x] Health checks
  - [x] Port mapping

### Deployment Files

- [x] Create `.env.example`
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
| Project Setup | 10 | 8 | 80% |
| GitHub Client | 6 | 4 | 67% |
| Heuristics | 24 | 24 | 100% |
| Scoring Engine | 4 | 4 | 100% |
| Webhook | 7 | 6 | 86% |
| Actions | 8 | 7 | 88% |
| Configuration | 4 | 4 | 100% |
| Testing | 5 | 5 | 100% |
| CI/CD | 1 | 1 | 100% |
| Deployment | 4 | 3 | 75% |
| Documentation | 3 | 0 | 0% |
| **Total** | **87** | **66** | **76%** |

*Database tasks (13) deferred to future phase*
