"""Pytest configuration and fixtures."""

import pytest

from dj_brevo.services import BrevoClient


@pytest.fixture
def brevo_client() -> BrevoClient:
    """Create a BrevoClient for testing."""
    return BrevoClient(api_key="test-api-key")


@pytest.fixture
def brevo_success_response() -> dict:
    """Standard successful response from Brevo API."""
    return {"messageId": "<202401151234.abc123@smtp-relay.brevo.com>"}
