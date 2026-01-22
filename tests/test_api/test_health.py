"""Tests for health check endpoints."""

from fastapi.testclient import TestClient

from pr_slop_stopper.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test the health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_check() -> None:
    """Test the readiness check endpoint returns ready status."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_root_endpoint() -> None:
    """Test the root endpoint returns expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "PR Slop Stopper is running"}
