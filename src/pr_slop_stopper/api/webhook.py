"""GitHub webhook handler."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from pr_slop_stopper.core.repo_config import RepoConfig
from pr_slop_stopper.github.models import PullRequestWebhookPayload
from pr_slop_stopper.types import GitHubClientProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret configured in GitHub App

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(signature, expected_signature)


async def process_pull_request(
    payload: PullRequestWebhookPayload,
    app_id: int,
    private_key: str,
) -> None:
    """Process a pull request event in the background.

    This function runs asynchronously after the webhook returns 202.

    Args:
        payload: Parsed webhook payload
        app_id: GitHub App ID
        private_key: GitHub App private key
    """
    # Import here to avoid circular imports
    from pr_slop_stopper.actions.executor import execute_action
    from pr_slop_stopper.core import ReputationScorer
    from pr_slop_stopper.core.repo_config import load_repo_config
    from pr_slop_stopper.github import GitHubClient

    repo_full_name = payload.repository.full_name
    pr_number = payload.number
    sender_login = payload.sender.login
    installation_id = payload.installation.id

    logger.info(
        "Processing PR #%d from %s in %s",
        pr_number,
        sender_login,
        repo_full_name,
    )

    try:
        # Initialize GitHub client
        client = GitHubClient(
            app_id=app_id,
            private_key=private_key,
            installation_id=installation_id,
        )

        # Load repo config
        config = load_repo_config(client, repo_full_name)

        # Check skip conditions
        if should_skip_user(client, repo_full_name, sender_login, config):
            logger.info("Skipping user %s (whitelisted or maintainer)", sender_login)
            return

        # Get user details for scoring
        user = client.client.get_user(sender_login)

        # Calculate score
        scorer = ReputationScorer(
            warning_threshold=config.warning_threshold,
            close_threshold=config.close_threshold,
        )
        result = scorer.calculate_score(
            user,  # type: ignore[arg-type]  # PyGithub types satisfy GitHubUserProtocol
            enabled_heuristics=config.enabled_heuristics,
        )

        logger.info(
            "Score for %s: %d (recommendation: %s)",
            sender_login,
            result.clamped_score,
            result.recommendation,
        )

        # Execute action based on score
        await execute_action(
            client=client,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            result=result,
            config=config,
        )

    except Exception:
        logger.exception("Error processing PR #%d in %s", pr_number, repo_full_name)


def should_skip_user(
    client: GitHubClientProtocol,
    repo_full_name: str,
    username: str,
    config: RepoConfig,
) -> bool:
    """Check if user should be skipped from scoring.

    Args:
        client: GitHubClient instance
        repo_full_name: Repository full name
        username: User login to check
        config: RepoConfig instance

    Returns:
        True if user should be skipped
    """
    # Check whitelist
    if username in config.whitelist:
        return True

    # Check if user is a collaborator/maintainer
    try:
        repo = client.get_repository(repo_full_name)
        if repo.has_in_collaborators(username):
            return True
    except Exception:
        logger.warning("Could not check collaborator status for %s", username)

    # Check if user has previously merged a PR to this repo
    try:
        merged_prs = client.client.search_issues(
            f"repo:{repo_full_name} is:pr is:merged author:{username}"
        )
        if merged_prs.totalCount > 0:
            return True
    except Exception:
        logger.warning("Could not check merged PRs for %s", username)

    return False


@router.post("/marketplace")
async def marketplace_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
) -> dict[str, str]:
    """Handle GitHub Marketplace webhook events.

    Logs marketplace events for monitoring app installations and subscription changes.
    """
    from pr_slop_stopper.config import get_settings

    settings = get_settings()

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_signature(body, x_hub_signature_256 or "", settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse and log payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    logger.info("Marketplace event: %s", payload)

    return {"status": "received"}


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
) -> dict[str, str | int]:
    """Handle GitHub webhook events.

    Returns 200 with status and processes the event in the background.
    """
    # Import settings lazily to allow for testing
    from pr_slop_stopper.config import get_settings

    settings = get_settings()

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_signature(body, x_hub_signature_256 or "", settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload_dict = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    # Only handle pull_request.opened events
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event type: {x_github_event}"}

    action = payload_dict.get("action")
    if action != "opened":
        return {"status": "ignored", "reason": f"action: {action}"}

    # Parse webhook payload
    try:
        payload = PullRequestWebhookPayload(**payload_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e

    # Process in background
    background_tasks.add_task(
        process_pull_request,
        payload,
        settings.github_app_id,
        settings.github_private_key,
    )

    return {"status": "accepted", "pr": payload.number}
