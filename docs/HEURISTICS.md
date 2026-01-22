# Heuristics Guide

This document details all reputation heuristics used by PR Slop Stop, including scoring weights and rationale.

## Scoring Philosophy

- **Starting point**: Every user begins at score **0** (neutral)
- **Range**: Scores can go from **-100** to **+100**
- **Bi-directional**: Positive signals add points, negative signals subtract
- **Cumulative**: All applicable heuristics are summed
- **Capped**: Final score is clamped to [-100, +100]

## Heuristic Categories

### 1. Profile Completeness

Legitimate contributors typically have complete GitHub profiles. Spam accounts often have minimal or no profile information.

| Signal | Score | Rationale |
|--------|-------|-----------|
| Has profile picture (not default) | +5 | Effort to personalize account |
| Has bio/description | +3 | Indicates real person |
| Has company/organization listed | +3 | Professional affiliation |
| Has location | +2 | Additional personalization |
| Has website/blog link | +3 | External presence |
| Has LinkedIn link matching name | +5 | Verified professional identity |
| Has Twitter/X link | +2 | Social presence |
| **No profile picture** | -5 | Default gravatar is suspicious |
| **No bio AND no links** | -5 | Completely empty profile |

**Maximum positive**: +23
**Maximum negative**: -10

### 2. Account Age

Newer accounts are more likely to be throwaway spam accounts. Established accounts have more to lose.

| Signal | Score | Rationale |
|--------|-------|-----------|
| Account age >= 5 years | +15 | Long-standing account |
| Account age >= 3 years | +10 | Established account |
| Account age >= 1 year | +5 | Not brand new |
| Account age >= 6 months | 0 | Neutral |
| Account age < 6 months | -10 | Very new account |
| **Account age < 3 months** | -15 | Likely created for spam |
| **Account age < 1 month** | -20 | Almost certainly suspicious |

**Note**: Only the single most applicable score is applied (not cumulative within this category).

### 3. PR Acceptance Rate

Users who consistently get PRs rejected are either learning (acceptable) or spamming (not acceptable). Pattern analysis helps distinguish.

| Signal | Score | Rationale |
|--------|-------|-----------|
| Any month (last 12) with 10+ PRs and <20% merge rate | -25 | Strong spam signal |
| Any month (last 12) with 5+ PRs and <20% merge rate | -15 | Moderate spam signal |
| Overall PR merge rate > 70% (min 5 PRs) | +10 | High-quality contributions |
| Overall PR merge rate > 50% (min 10 PRs) | +5 | Decent track record |
| **High volume of closed PRs with negative comments** | -20 | Maintainers flagged as spam |

### 4. Notable OSS Contributions

Contributions to well-known, reputable open source organizations are strong positive signals.

| Signal | Score | Rationale |
|--------|-------|-----------|
| Merged PR to Apache project | +15 | Vetted by major foundation |
| Merged PR to Linux Foundation project | +15 | Kernel-level trust |
| Merged PR to CNCF project | +12 | Cloud native community trust |
| Merged PR to Mozilla project | +12 | Established OSS org |
| Merged PR to Kubernetes | +12 | Major project acceptance |
| Merged PR to Rust project | +10 | Quality-focused community |
| Merged PR to Python (CPython/PyPI) | +10 | Core ecosystem |
| Merged PR to Node.js | +10 | Core ecosystem |
| Merged PR to Django | +8 | Popular framework |
| Merged PR to Rails | +8 | Popular framework |
| Merged PR to Terraform | +8 | HashiCorp project |
| Merged PR to Prometheus | +8 | Monitoring standard |

**Maximum positive**: +30 (capped to prevent gaming by contributing to many)

**Notable Organizations List**:
- Apache Software Foundation (`apache/*`)
- Linux Foundation (`torvalds/linux`, `linuxfoundation/*`)
- CNCF (`cncf/*`, `kubernetes/*`, `prometheus/*`, `envoyproxy/*`)
- Mozilla (`mozilla/*`)
- Rust (`rust-lang/*`)
- Python (`python/*`)
- Node.js (`nodejs/*`)
- Django (`django/*`)
- Rails (`rails/*`)
- HashiCorp (`hashicorp/*`)

### 5. Activity Patterns

Suspicious activity patterns often indicate automated or spam behavior.

| Signal | Score | Rationale |
|--------|-------|-----------|
| Consistent activity over 2+ years | +10 | Sustained engagement |
| Regular commits to own repos | +5 | Active developer |
| **Burst of activity after years dormant** | -15 | Account potentially compromised or sold |
| **10+ PRs in a year to repos with <10K stars** | -10 | Gaming contribution metrics |
| **Fork created <24h before PR** | -10 | No development history |
| **PRs only to repos never starred/engaged** | -8 | Drive-by contributions |

### 6. Follower Patterns

Social signals on GitHub can indicate legitimacy.

| Signal | Score | Rationale |
|--------|-------|-----------|
| 50+ followers | +8 | Community recognition |
| 20+ followers | +5 | Some recognition |
| 5+ followers | +2 | Basic social proof |
| **Following 500+ but <10 followers** | -10 | Bot-like behavior |
| **Following/follower ratio > 50:1** | -8 | Follow-spam pattern |

### 7. Contribution Type Patterns

Certain contribution patterns are common among spam PRs.

| Signal | Score | Rationale |
|--------|-------|-----------|
| History of code contributions (not just docs) | +5 | Substantive contributor |
| **PRs exclusively touching docs/typos (5+)** | -12 | Common spam pattern |
| **Multiple PRs with identical patterns** | -10 | Automated submission |

### 8. Maintainer Feedback Signals

If maintainers have previously flagged this user's PRs as spam, that's highly informative.

| Signal | Score | Rationale |
|--------|-------|-----------|
| **3+ PRs closed with "spam" label** | -30 | Community consensus |
| **3+ PRs closed with comments like "AI generated", "LLM", "GPT"** | -25 | Explicit spam identification |
| **Blocked by any repo in this org** | -20 | Org-level trust broken |

## Heuristic Weights Summary

| Category | Max Positive | Max Negative |
|----------|--------------|--------------|
| Profile Completeness | +23 | -10 |
| Account Age | +15 | -20 |
| PR Acceptance Rate | +10 | -25 |
| Notable OSS Contributions | +30 | 0 |
| Activity Patterns | +15 | -43 |
| Follower Patterns | +8 | -10 |
| Contribution Type Patterns | +5 | -22 |
| Maintainer Feedback | 0 | -30 |

**Theoretical Maximum**: +106 (capped to +100)
**Theoretical Minimum**: -160 (capped to -100)

## Default Thresholds

| Threshold | Default Score | Action |
|-----------|---------------|--------|
| Pass | >= -10 | No action |
| Warn | < -10, >= -40 | Add warning label |
| Close | < -40 | Add spam label + close |

## Future Heuristics (v2+)

These require more advanced analysis and are planned for future versions:

- **PR description analysis** - LLM-based quality assessment
- **Code change semantic analysis** - Does the code match the stated purpose?
- **Cross-reference with known spam databases**
- **Behavioral fingerprinting** - Timing patterns, commit message styles

## Tuning & Updates

Heuristic weights will be tuned based on:
1. False positive/negative rates from production data
2. Community feedback
3. Evolving spam patterns

Major weight changes will be documented in CHANGELOG.md.
