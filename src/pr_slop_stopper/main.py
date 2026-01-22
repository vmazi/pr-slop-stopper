"""FastAPI application entry point."""

from fastapi import FastAPI

from pr_slop_stopper.api.health import router as health_router
from pr_slop_stopper.api.webhook import router as webhook_router

app = FastAPI(
    title="PR Slop Stopper",
    description="GitHub App to combat AI-generated spam PRs using heuristic-based reputation scoring",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(webhook_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "PR Slop Stopper is running"}
