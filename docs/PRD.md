# Product Requirements Document: PR Slop Stop

## Problem Statement

### Background

The rise of Large Language Models (LLMs) has led to an explosion of AI-generated pull requests to open source repositories. While AI can be a legitimate tool for development, bad actors are using LLMs to:

1. **Farm GitHub contributions** for resume building
2. **Game "hacktoberfest" style events** with low-effort PRs
3. **Submit mass "fixes"** (typos, formatting, documentation) that are often incorrect or unnecessary
4. **Overwhelm maintainers** with PRs that require time to review and reject

### Impact

- **Maintainer burnout** - Reviewing and rejecting spam PRs is demoralizing and time-consuming
- **Legitimate contributors overlooked** - Real PRs get buried in spam
- **Trust erosion** - Maintainers become suspicious of all first-time contributors
- **Project health metrics corrupted** - Open PR counts become meaningless

### Current State

Most organizations have no automated defense against this pattern. Maintainers must manually:
- Review each PR
- Investigate contributor history
- Make judgment calls on legitimacy
- Write rejection comments
- Close PRs

This manual process doesn't scale.

## Solution Overview

PR Slop Stop is a GitHub App that automatically analyzes the reputation of PR authors and flags suspicious contributions before maintainers spend time reviewing them.

### Core Principles

1. **Start at zero** - Every user begins with a neutral score (0)
2. **Bi-directional scoring** - Positive signals increase score, negative signals decrease it
3. **Transparency** - Users can see why they were flagged
4. **Configurable** - Organizations control their own thresholds
5. **Non-blocking by default** - Warning labels before auto-close

### Target Users

1. **Open source maintainers** - Primary users who install and configure the app
2. **Organization admins** - Set org-wide policies
3. **Contributors** - Indirectly affected; should understand why they're flagged

## Functional Requirements

### FR-1: GitHub App Installation

- Install on individual repositories or entire organizations
- Request minimal permissions needed for operation
- Provide clear explanation of data accessed during installation

### FR-2: PR Event Handling

- Trigger on `pull_request.opened` events
- Skip analysis for:
  - Repository maintainers/collaborators
  - Users who have previously merged a PR to this repo
  - Whitelisted usernames
- Perform reputation analysis for all other PR authors

### FR-3: Reputation Scoring

- Calculate reputation score from -100 to +100
- Start at 0 (neutral)
- Apply heuristic weights (see HEURISTICS.md)
- Cache scores with configurable TTL (default: 24 hours)

### FR-4: Configurable Actions

Based on score thresholds, the app should:

| Score Range | Default Action |
|-------------|----------------|
| >= warn threshold | No action (pass) |
| < warn, >= close | Add warning label + explanatory comment |
| < close threshold | Add spam label + comment + close PR |

Maintainers configure thresholds via `.github/pr-slop-stop.yml`.

### FR-5: Labeling

Apply labels to flagged PRs:
- `pr-slop-stop: warning` - Suspicious but not conclusive
- `pr-slop-stop: likely-spam` - High confidence spam

Create labels automatically if they don't exist.

### FR-6: Comments

Add a comment explaining:
- The calculated reputation score
- Which heuristics contributed positively/negatively
- How to appeal (future feature)
- Link to documentation

### FR-7: Whitelist Management

- Per-repository whitelist in config file
- Organization-wide whitelist (future)
- Automatic whitelist for users who've had PRs merged

### FR-8: Configuration

Support `.github/pr-slop-stop.yml` with:
```yaml
thresholds:
  warn: -10
  close: -40

whitelist:
  - username1
  - username2

heuristics:
  profile_completeness: true
  account_age: true
  # ... etc
```

### FR-9: Logging & Metrics

- Log all scoring decisions
- Track metrics:
  - PRs analyzed
  - PRs flagged (warning vs. closed)
  - False positive reports (future)
- Expose metrics endpoint for monitoring

## Non-Functional Requirements

### NFR-1: Performance

- Score calculation should complete within 5 seconds
- Use caching to minimize GitHub API calls
- Handle rate limiting gracefully

### NFR-2: Scalability

- Support organizations with 100+ repositories
- Handle burst traffic during events (e.g., Hacktoberfest)

### NFR-3: Reliability

- 99.9% uptime target
- Graceful degradation if GitHub API is unavailable
- Queue-based processing for resilience

### NFR-4: Security

- Minimal permission scope
- No storage of sensitive data
- Audit logging for all actions

### NFR-5: Privacy

- Only access public profile information
- No tracking across organizations
- Data retention policy (delete after 30 days)

## Future Enhancements (Out of Scope for v1)

1. **Appeal process** - Allow flagged users to request review
2. **Issue analysis** - Extend to GitHub Issues
3. **Comment analysis** - Detect spam comments
4. **LLM-based analysis** - Analyze PR description and code quality
5. **Organization-wide whitelist** - Centralized whitelist management
6. **Dashboard** - Web UI for viewing statistics and managing config
7. **Webhook notifications** - Notify maintainers via Slack/Discord

## Success Metrics

1. **Adoption** - Number of installations
2. **Effectiveness** - % of spam PRs caught (requires labeling ground truth)
3. **False positive rate** - % of legitimate PRs incorrectly flagged
4. **Maintainer time saved** - Survey-based measurement

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives harm new contributors | High | Conservative default thresholds, clear appeal path |
| Gaming the heuristics | Medium | Regular heuristic updates, multiple signals required |
| GitHub API rate limits | Medium | Aggressive caching, request batching |
| Privacy concerns | Medium | Minimal data collection, transparency about what's analyzed |
| Maintainer configuration burden | Low | Sensible defaults, optional config |
