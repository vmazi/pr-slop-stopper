"""GitHub API client wrapper for PR Slop Stopper."""

from dataclasses import dataclass

from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from pr_slop_stopper.github.auth import get_installation_client


@dataclass
class GitHubClient:
    """Wrapper around PyGithub for PR Slop Stopper operations."""

    app_id: int
    private_key: str
    installation_id: int
    _client: Github | None = None

    @property
    def client(self) -> Github:
        """Lazily initialize and return the GitHub client."""
        if self._client is None:
            self._client = get_installation_client(
                self.app_id,
                self.private_key,
                self.installation_id,
            )
        return self._client

    def get_repository(self, full_name: str) -> Repository:
        """Get a repository by full name (owner/repo).

        Args:
            full_name: Repository full name like 'owner/repo'.

        Returns:
            The Repository object.
        """
        return self.client.get_repo(full_name)

    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest:
        """Get a pull request by repository and PR number.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.

        Returns:
            The PullRequest object.
        """
        repo = self.get_repository(repo_full_name)
        return repo.get_pull(pr_number)

    def add_label(self, repo_full_name: str, pr_number: int, label: str) -> None:
        """Add a label to a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
            label: The label name to add.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.add_to_labels(label)

    def add_comment(self, repo_full_name: str, pr_number: int, body: str) -> None:
        """Add a comment to a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
            body: The comment body.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.create_issue_comment(body)

    def close_pull_request(self, repo_full_name: str, pr_number: int) -> None:
        """Close a pull request.

        Args:
            repo_full_name: Repository full name like 'owner/repo'.
            pr_number: The pull request number.
        """
        pr = self.get_pull_request(repo_full_name, pr_number)
        pr.edit(state="closed")
