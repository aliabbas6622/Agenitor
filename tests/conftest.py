"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def app():
    """Create a fresh FastAPI app for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """Synchronous test client for the FastAPI app."""
    return TestClient(app)
