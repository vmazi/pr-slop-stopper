# Contribution Type Patterns - Implementation Details

## Overview

This heuristic analyzes the types of contributions a user makes. Legitimate developers typically make substantive code contributions, while spam accounts often focus on low-effort changes like documentation typos, which are easier to automate and less likely to be scrutinized.

## Scoring Reference

| Signal | Score | Detection Method |
|--------|-------|------------------|
| History of code contributions (not just docs) | +5 | PR file type analysis |
| PRs exclusively touching docs/typos (5+) | -12 | PR file pattern analysis |
| Multiple PRs with identical patterns | -10 | PR diff similarity |

## PyGithub API Usage

### Get PR Files

```python
from github import Github

def get_pr_files(g: Github, repo_full_name: str, pr_number: int) -> list:
    """
    Get list of files changed in a PR.

    Returns file objects with filename, status, additions, deletions, etc.
    """
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    files = pr.get_files()
    return list(files)
```

### PR File Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `filename` | `str` | Path to the file |
| `status` | `str` | "added", "removed", "modified", "renamed" |
| `additions` | `int` | Lines added |
| `deletions` | `int` | Lines deleted |
| `changes` | `int` | Total lines changed |
| `patch` | `str` | The actual diff content |

## File Type Classification

```python
# Documentation file patterns
DOC_PATTERNS = [
    r'README\.md$',
    r'CHANGELOG\.md$',
    r'CONTRIBUTING\.md$',
    r'LICENSE.*$',
    r'\.md$',
    r'\.rst$',
    r'\.txt$',
    r'docs?/',
    r'documentation/',
]

# Config/metadata patterns (low-effort but not necessarily spam)
CONFIG_PATTERNS = [
    r'\.json$',
    r'\.ya?ml$',
    r'\.toml$',
    r'\.ini$',
    r'\.cfg$',
    r'\.env',
    r'Makefile$',
    r'Dockerfile$',
]

# Code file patterns (substantive contributions)
CODE_PATTERNS = [
    r'\.py$',
    r'\.js$',
    r'\.ts$',
    r'\.jsx$',
    r'\.tsx$',
    r'\.go$',
    r'\.rs$',
    r'\.java$',
    r'\.c$',
    r'\.cpp$',
    r'\.h$',
    r'\.rb$',
    r'\.php$',
    r'\.swift$',
    r'\.kt$',
    r'\.scala$',
    r'\.cs$',
    r'\.sh$',
    r'\.sql$',
]

# Test file patterns
TEST_PATTERNS = [
    r'test[s]?/',
    r'spec[s]?/',
    r'_test\.',
    r'\.test\.',
    r'\.spec\.',
    r'test_',
]
```

## Implementation

```python
from dataclasses import dataclass
from collections import defaultdict
import re
from github import Github
import structlog

logger = structlog.get_logger()


DOC_PATTERNS = [
    r'README\.md$',
    r'CHANGELOG\.md$',
    r'CONTRIBUTING\.md$',
    r'LICENSE',
    r'\.md$',
    r'\.rst$',
    r'docs?/',
]

CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java',
    '.c', '.cpp', '.h', '.hpp', '.rb', '.php', '.swift', '.kt',
    '.scala', '.cs', '.sh', '.sql', '.vue', '.svelte',
}


@dataclass
class FileClassification:
    filename: str
    category: str  # "code", "docs", "config", "test", "other"
    additions: int
    deletions: int


@dataclass
class PRAnalysis:
    pr_number: int
    repo: str
    total_files: int
    code_files: int
    doc_files: int
    config_files: int
    test_files: int
    is_docs_only: bool
    total_additions: int
    total_deletions: int


@dataclass
class ContributionTypeResult:
    score: int
    breakdown: dict[str, int]
    prs_analyzed: int
    pr_analyses: list[PRAnalysis]
    has_code_contributions: bool
    docs_only_count: int
    pattern_similarity_detected: bool


def classify_file(filename: str) -> str:
    """Classify a file as code, docs, config, test, or other."""
    filename_lower = filename.lower()

    # Check for test files first
    for pattern in [r'test[s]?/', r'spec[s]?/', r'_test\.', r'\.test\.', r'\.spec\.', r'test_']:
        if re.search(pattern, filename_lower):
            return "test"

    # Check for docs
    for pattern in DOC_PATTERNS:
        if re.search(pattern, filename_lower):
            return "docs"

    # Check for code by extension
    ext = '.' + filename.split('.')[-1] if '.' in filename else ''
    if ext.lower() in CODE_EXTENSIONS:
        return "code"

    # Check for config
    config_exts = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.env'}
    if ext.lower() in config_exts:
        return "config"

    return "other"


def analyze_pr_files(g: Github, repo_full_name: str, pr_number: int) -> PRAnalysis:
    """Analyze the files changed in a single PR."""
    try:
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = list(pr.get_files())

        classifications = defaultdict(int)
        total_additions = 0
        total_deletions = 0

        for f in files:
            category = classify_file(f.filename)
            classifications[category] += 1
            total_additions += f.additions
            total_deletions += f.deletions

        total_files = len(files)
        code_files = classifications.get("code", 0)
        doc_files = classifications.get("docs", 0)
        test_files = classifications.get("test", 0)
        config_files = classifications.get("config", 0)

        # PR is docs-only if all files are docs
        is_docs_only = (
            doc_files > 0 and
            code_files == 0 and
            test_files == 0
        )

        return PRAnalysis(
            pr_number=pr_number,
            repo=repo_full_name,
            total_files=total_files,
            code_files=code_files,
            doc_files=doc_files,
            config_files=config_files,
            test_files=test_files,
            is_docs_only=is_docs_only,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )

    except Exception as e:
        logger.warning("pr_file_analysis_failed", repo=repo_full_name, pr=pr_number, error=str(e))
        return None


def detect_pattern_similarity(pr_analyses: list[PRAnalysis]) -> bool:
    """
    Detect if multiple PRs follow suspiciously similar patterns.

    Indicators:
    - All PRs touch same number of files
    - All PRs have similar additions/deletions
    - All PRs touch same file types
    """
    if len(pr_analyses) < 3:
        return False

    # Check if file counts are suspiciously uniform
    file_counts = [pr.total_files for pr in pr_analyses]
    if len(set(file_counts)) == 1 and file_counts[0] <= 3:
        # All PRs touch exactly the same number of files (small number)
        return True

    # Check if all PRs are docs-only
    docs_only_count = sum(1 for pr in pr_analyses if pr.is_docs_only)
    if docs_only_count == len(pr_analyses) and len(pr_analyses) >= 5:
        return True

    # Check for similar change sizes
    change_sizes = [(pr.total_additions, pr.total_deletions) for pr in pr_analyses]
    unique_sizes = set(change_sizes)
    if len(unique_sizes) <= 2 and len(pr_analyses) >= 5:
        # Very uniform change patterns
        return True

    return False


def calculate_contribution_type_patterns(
    g: Github,
    username: str,
    max_prs_to_analyze: int = 20,
) -> ContributionTypeResult:
    """
    Calculate contribution type patterns score for a GitHub user.

    Args:
        g: PyGithub Github instance
        username: GitHub username to analyze
        max_prs_to_analyze: Maximum number of PRs to analyze

    Returns:
        ContributionTypeResult with score and analysis details
    """
    score = 0
    breakdown = {}

    # Search for user's recent PRs
    query = f"author:{username} type:pr"
    try:
        results = g.search_issues(query, sort="created", order="desc")
        prs = list(results)[:max_prs_to_analyze]
    except Exception as e:
        logger.error("pr_search_failed", username=username, error=str(e))
        return ContributionTypeResult(
            score=0,
            breakdown={"error": 0},
            prs_analyzed=0,
            pr_analyses=[],
            has_code_contributions=False,
            docs_only_count=0,
            pattern_similarity_detected=False,
        )

    if not prs:
        return ContributionTypeResult(
            score=0,
            breakdown={"no_prs": 0},
            prs_analyzed=0,
            pr_analyses=[],
            has_code_contributions=False,
            docs_only_count=0,
            pattern_similarity_detected=False,
        )

    # Analyze each PR
    pr_analyses = []
    for pr_issue in prs:
        try:
            repo_name = pr_issue.repository.full_name
            analysis = analyze_pr_files(g, repo_name, pr_issue.number)
            if analysis:
                pr_analyses.append(analysis)
        except Exception as e:
            logger.warning("pr_analysis_skipped", pr=pr_issue.number, error=str(e))
            continue

    if not pr_analyses:
        return ContributionTypeResult(
            score=0,
            breakdown={"analysis_failed": 0},
            prs_analyzed=0,
            pr_analyses=[],
            has_code_contributions=False,
            docs_only_count=0,
            pattern_similarity_detected=False,
        )

    # Calculate metrics
    has_code_contributions = any(pr.code_files > 0 for pr in pr_analyses)
    docs_only_count = sum(1 for pr in pr_analyses if pr.is_docs_only)
    pattern_similarity = detect_pattern_similarity(pr_analyses)

    # Positive signal: Has substantive code contributions
    if has_code_contributions:
        score += 5
        breakdown["code_contributions"] = 5

    # Negative signal: PRs exclusively touching docs (5+)
    if docs_only_count >= 5:
        score -= 12
        breakdown["docs_only_spam"] = -12

    # Negative signal: Multiple PRs with identical patterns
    if pattern_similarity:
        score -= 10
        breakdown["pattern_similarity"] = -10

    return ContributionTypeResult(
        score=score,
        breakdown=breakdown,
        prs_analyzed=len(pr_analyses),
        pr_analyses=pr_analyses,
        has_code_contributions=has_code_contributions,
        docs_only_count=docs_only_count,
        pattern_similarity_detected=pattern_similarity,
    )
```

## API Calls Required

| Operation | API Call | Rate Limit Impact |
|-----------|----------|-------------------|
| Search user PRs | `g.search_issues(query)` | 30/minute (Search API) |
| Get PR files | `pr.get_files()` | 1 request per PR |

**Total requests**: 1 search + N PR file fetches (where N = min(PRs found, max_prs_to_analyze))

For 20 PRs: ~21 requests

## Optimization: Sampling Strategy

```python
def smart_sample_prs(prs: list, max_sample: int = 20) -> list:
    """
    Smart sampling of PRs for analysis.

    Strategy: Take a mix of recent and older PRs to detect both
    current behavior and historical patterns.
    """
    if len(prs) <= max_sample:
        return prs

    # Take 60% recent, 40% spread across history
    recent_count = int(max_sample * 0.6)
    historical_count = max_sample - recent_count

    recent = prs[:recent_count]

    # Sample from the rest
    remaining = prs[recent_count:]
    step = len(remaining) // historical_count if historical_count > 0 else 1
    historical = remaining[::step][:historical_count]

    return recent + historical
```

## Edge Cases

1. **Legitimate doc contributors**: Some users legitimately focus on documentation. Consider context (e.g., tech writers).

2. **Mixed PRs**: A PR touching both code and docs should be counted as code contribution.

3. **Generated files**: Some code files are auto-generated (e.g., from protobuf). These shouldn't count as substantive.

4. **Monorepo PRs**: PRs to monorepos might touch many files across different categories.

5. **Tiny changes**: A 1-line code change might be less valuable than substantial doc improvements.

## Testing Considerations

```python
def test_docs_only_detection():
    """Test detection of docs-only PR patterns."""
    mock_prs = [
        create_mock_pr(files=[("README.md", "docs"), ("CONTRIBUTING.md", "docs")]),
        create_mock_pr(files=[("docs/guide.md", "docs")]),
        create_mock_pr(files=[("README.md", "docs")]),
        create_mock_pr(files=[("CHANGELOG.md", "docs")]),
        create_mock_pr(files=[("docs/api.md", "docs")]),
    ]

    result = calculate_with_mock(mock_prs)
    assert result.docs_only_count == 5
    assert "docs_only_spam" in result.breakdown
    assert result.score <= -12


def test_code_contributions():
    """Test that code contributions are rewarded."""
    mock_prs = [
        create_mock_pr(files=[("src/main.py", "code"), ("README.md", "docs")]),
        create_mock_pr(files=[("lib/utils.js", "code")]),
    ]

    result = calculate_with_mock(mock_prs)
    assert result.has_code_contributions == True
    assert "code_contributions" in result.breakdown


def test_pattern_similarity():
    """Test detection of suspiciously similar PRs."""
    # All PRs touch exactly 1 file with similar changes
    mock_prs = [
        create_mock_pr(files=[("README.md", "docs")], additions=2, deletions=1),
        create_mock_pr(files=[("README.md", "docs")], additions=2, deletions=1),
        create_mock_pr(files=[("README.md", "docs")], additions=2, deletions=1),
        create_mock_pr(files=[("README.md", "docs")], additions=2, deletions=1),
        create_mock_pr(files=[("README.md", "docs")], additions=2, deletions=1),
    ]

    result = calculate_with_mock(mock_prs)
    assert result.pattern_similarity_detected == True
```

## Caching Considerations

PR content doesn't change, but new PRs are created:

```python
# Cache individual PR analyses
# Cache key: f"pr_analysis:{repo}:{pr_number}"
# TTL: 7 days (PR files don't change)

# Cache overall result
# Cache key: f"contribution_type:{username}"
# TTL: 6-12 hours (new PRs may be created)
```

## Future Improvements

1. **Change quality analysis**: Analyze the actual diff content, not just file types.

2. **PR title/description analysis**: Spam PRs often have templated titles like "Fix typo in README".

3. **Commit message analysis**: Check for repetitive or low-quality commit messages.

4. **PR size weighting**: A 500-line code PR is more significant than a 5-line PR.

5. **Language-specific analysis**: Understand if changes are substantive for specific languages.

6. **Review engagement**: Did the user engage with review comments, or just submit and abandon?
