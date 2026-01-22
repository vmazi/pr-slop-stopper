"""GitHub App authentication using PyGithub."""

import time

import jwt
from github import Auth, Github, GithubIntegration


def create_jwt(app_id: int, private_key: str) -> str:
    """Create a JWT for GitHub App authentication.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key (PEM format).

    Returns:
        A JWT token valid for 10 minutes.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds ago to handle clock skew
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_installation_client(
    app_id: int,
    private_key: str,
    installation_id: int,
) -> Github:
    """Get an authenticated GitHub client for a specific installation.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key (PEM format).
        installation_id: The installation ID from the webhook payload.

    Returns:
        An authenticated Github client for the installation.
    """
    auth = Auth.AppAuth(app_id, private_key)
    gi = GithubIntegration(auth=auth)
    installation_auth = gi.get_access_token(installation_id)
    return Github(auth=Auth.Token(installation_auth.token))


def get_app_integration(app_id: int, private_key: str) -> GithubIntegration:
    """Get a GithubIntegration instance for app-level operations.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key (PEM format).

    Returns:
        A GithubIntegration instance.
    """
    auth = Auth.AppAuth(app_id, private_key)
    return GithubIntegration(auth=auth)
