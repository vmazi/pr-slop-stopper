# PR Slop Stopper

A GitHub App that combats AI-generated spam pull requests by analyzing contributor reputation using heuristic-based scoring.

## The Problem

Open source organizations are increasingly inundated with low-quality, LLM-generated pull requests that:
- Waste precious maintainer review cycles
- Often propose invalid or unnecessary changes
- Game contribution metrics without providing real value
- Erode trust in the open source contribution process

## The Solution

PR Slop Stopper analyzes the GitHub profile and activity history of PR authors to calculate a reputation score. PRs from accounts with suspicious patterns are automatically flagged or closed based on configurable thresholds.

### Key Features

- **Heuristic-based scoring** - Analyzes profile completeness, contribution history, PR acceptance rates, and activity patterns
- **Configurable sensitivity** - Maintainers set thresholds for warning labels vs. auto-close
- **Whitelist support** - Known-good contributors can be exempted
- **Non-invasive** - Only evaluates PRs from users who have never merged a commit to the repo
- **Transparent** - Adds labels and comments explaining why a PR was flagged

## Scoring Heuristics

PR Slop Stopper uses 8 heuristics to evaluate contributors:

| Heuristic | Description | Score Range |
|-----------|-------------|-------------|
| **Account Age** | Newer accounts score lower | -20 to +15 |
| **Profile Completeness** | Complete profiles (bio, avatar, etc.) score higher | -10 to +23 |
| **Follower Patterns** | Detects follow-spam patterns | -10 to +8 |
| **PR Acceptance Rate** | Historical merge rate across repos | -25 to +10 |
| **Contribution Type** | Detects docs-only spam patterns | -15 to +10 |
| **Activity Patterns** | Detects burst/dormancy patterns | -20 to +10 |
| **Notable Contributions** | Contributions to popular OSS repos | -10 to +20 |
| **Fork Timing** | Detects instant fork-to-PR pattern | -20 to +10 |

Final scores are clamped to the range [-100, +100].

## Configuration

Create `.github/pr-slop-stopper.yml` in your repository:

```yaml
# Score thresholds (scores range from -100 to +100)
thresholds:
  warn: -10      # Add warning label at this score
  close: -40    # Auto-close PR at this score

# Whitelisted GitHub usernames (exempt from checks)
whitelist:
  - trusted-bot
  - known-contributor

# Enable/disable specific heuristics
heuristics:
  account_age: true
  profile_completeness: true
  follower_patterns: true
  pr_acceptance_rate: true
  contribution_type: true
  activity_patterns: true
  notable_contributions: true
  fork_timing: true

# Action settings
actions:
  add_label: true         # Add labels to flagged PRs
  add_comment: true       # Add explanation comment
  auto_close: false       # Auto-close PRs at close threshold (disabled by default)
  add_passed_label: true  # Add label when PR passes checks (default: on)

# Custom label names (optional)
labels:
  passed: "pr-slop-stopper: passed-checks"
  warning: "pr-slop-stopper: warning"
  spam: "pr-slop-stopper: likely-spam"
```

## Skip Conditions

PRs are **not scored** if the author:
1. Is listed in the repository whitelist
2. Is a collaborator or maintainer of the repository
3. Has previously merged a PR to the repository

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/pr-slop-stopper.git
cd pr-slop-stopper

# Set up development environment
source devenv.sh
```

The `devenv.sh` script:
- Syncs dependencies with uv
- Activates the virtual environment
- Sets up helpful aliases

### Available Commands

After sourcing `devenv.sh`:

```bash
test      # Run pytest with verbose output
lint      # Run ruff linter
lintfix   # Run ruff linter with auto-fix
fmt       # Format code with ruff
fmtcheck  # Check code formatting
typecheck # Run type checker
check     # Run all checks (lint, format, typecheck, test)
serve     # Start development server with auto-reload
```

### Manual Commands

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest -v

# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check src/

# Build container
./build.sh
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# GitHub App Configuration
GITHUB_APP_ID=your_app_id
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

## Deployment

### Architecture

PR Slop Stopper runs as a containerized FastAPI application behind a Caddy reverse proxy:

```
Internet -> Caddy (TLS) -> shared_network -> pr-slop-stopper:8000
```

### Container Deployment

```bash
# Build the container
./build.sh

# Or manually
podman build -t pr-slop-stopper -f Containerfile .

# Create podman secrets (one-time setup)
echo "your_app_id" | podman secret create GITHUB_APP_ID -
cat /path/to/private-key.pem | podman secret create GITHUB_PRIVATE_KEY -
echo "your_webhook_secret" | podman secret create GITHUB_WEBHOOK_SECRET -

# Run with podman-compose
podman-compose up -d
```

The container joins `shared_network` to be accessible from Caddy. Secrets are injected as environment variables using podman's secret management.

## Documentation

- [Product Requirements](docs/PRD.md) - Detailed problem statement and requirements
- [Heuristics Guide](docs/HEURISTICS.md) - Scoring criteria and weights
- [Architecture](docs/ARCHITECTURE.md) - Technical design and implementation details

## Status

In Development - Not yet available for public installation.

## License

MIT
