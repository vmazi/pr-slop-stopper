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

## Quick Start

1. Install the GitHub App on your organization
2. Configure sensitivity thresholds in `.github/pr-slop-stopper.yml`
3. Optionally add whitelisted users

## Documentation

- [Product Requirements](docs/PRD.md) - Detailed problem statement and requirements
- [Heuristics Guide](docs/HEURISTICS.md) - Scoring criteria and weights
- [Architecture](docs/ARCHITECTURE.md) - Technical design and implementation details

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
  profile_completeness: true
  account_age: true
  pr_acceptance_rate: true
  notable_contributions: true
  activity_patterns: true
```

## Status

🚧 **In Development** - Not yet available for installation

## License

MIT
