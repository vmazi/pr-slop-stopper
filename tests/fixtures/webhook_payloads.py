"""Sample webhook payloads for testing."""


def make_pr_opened_payload(
    *,
    pr_number: int = 1,
    action: str = "opened",
    sender_login: str = "test-user",
    repo_full_name: str = "owner/repo",
    installation_id: int = 12345,
) -> dict:
    """Generate a pull_request.opened webhook payload.

    Args:
        pr_number: Pull request number
        action: The action type (opened, closed, etc.)
        sender_login: The GitHub username of the PR author
        repo_full_name: Repository full name (owner/repo)
        installation_id: GitHub App installation ID

    Returns:
        Dictionary representing the webhook payload
    """
    owner, repo = repo_full_name.split("/")
    return {
        "action": action,
        "number": pr_number,
        "pull_request": {
            "id": 1000000 + pr_number,
            "number": pr_number,
            "state": "open",
            "title": f"Test PR #{pr_number}",
            "body": "This is a test pull request",
            "html_url": f"https://github.com/{repo_full_name}/pull/{pr_number}",
            "user": {
                "login": sender_login,
                "id": 123456,
                "type": "User",
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
                "sha": "789xyz000",
            },
        },
        "repository": {
            "id": 999999,
            "name": repo,
            "full_name": repo_full_name,
            "html_url": f"https://github.com/{repo_full_name}",
            "owner": {
                "login": owner,
                "id": 111111,
                "type": "User",
            },
            "private": False,
        },
        "sender": {
            "login": sender_login,
            "id": 123456,
            "type": "User",
        },
        "installation": {
            "id": installation_id,
        },
    }


# Pre-built payloads for common test scenarios
PR_OPENED_PAYLOAD = make_pr_opened_payload()

PR_CLOSED_PAYLOAD = make_pr_opened_payload(action="closed")

PR_REOPENED_PAYLOAD = make_pr_opened_payload(action="reopened")
