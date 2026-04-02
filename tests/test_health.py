"""Health endpoint tests."""

from __future__ import annotations


def test_health_check(client):
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "version" in data


def test_health_detailed(client):
    """GET /health/detailed returns 200 with component statuses."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert "redis" in data
    assert "celery" in data
