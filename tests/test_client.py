"""Tests for the Brevo API client."""

import pytest
from pytest_httpx import HTTPXMock

from dj_brevo.exceptions import (
    BrevoAPIError,
    BrevoAuthError,
    BrevoConfigError,
    BrevoRateLimitError,
)
from dj_brevo.services import BrevoClient


class TestBrevoClientInit:
    """Tests for BrevoClient initialization."""

    def test_client_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client should raise error if no API key provided."""
        # Remove API_KEY from settings so there's no fallback
        monkeypatch.setattr(
            "dj_brevo.services.client.brevo_settings",
            type(
                "FakeSettings",
                (),
                {
                    "API_KEY": None,
                    "API_BASE_URL": "https://api.brevo.com/v3",
                    "TIMEOUT": 10,
                },
            )(),
        )

        with pytest.raises(BrevoConfigError, match="API key"):
            BrevoClient(api_key=None)

    def test_client_accepts_explicit_api_key(self) -> None:
        """Client should accept an explicitly provided API key."""
        client = BrevoClient(api_key="my-test-key")
        assert client.api_key == "my-test-key"


class TestSendEmail:
    """Tests for the send_email method."""

    def test_send_email_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
        brevo_success_response: dict,
    ) -> None:
        """Successful email send should return message ID."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        result = brevo_client.send_email(
            to=[{"email": "recipient@example.com"}],
            subject="Test Subject",
            html_content="<p>Hello!</p>",
            sender={"email": "sender@example.com"},
        )

        assert "messageId" in result

    def test_send_email_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
        brevo_success_response: dict,
    ) -> None:
        """Send email should build the correct API payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        brevo_client.send_email(
            to=[{"email": "recipient@example.com", "name": "Recipient"}],
            subject="Test Subject",
            html_content="<p>Hello!</p>",
            sender={"email": "sender@example.com"},
            text_content="Hello!",
        )

        # Check what was actually sent
        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload["to"] == [
            {"email": "recipient@example.com", "name": "Recipient"}
        ]
        assert payload["subject"] == "Test Subject"
        assert payload["htmlContent"] == "<p>Hello!</p>"
        assert payload["textContent"] == "Hello!"

    def test_send_email_auth_error(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should raise BrevoAuthError on 401 response."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            status_code=401,
            json={"message": "Invalid API key"},
        )

        with pytest.raises(BrevoAuthError) as exc_info:
            brevo_client.send_email(
                to=[{"email": "test@example.com"}],
                subject="Test",
                html_content="<p>Test</p>",
                sender={"email": "sender@example.com"},
            )

        assert exc_info.value.status_code == 401

    def test_send_email_rate_limit_error(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should raise BrevoRateLimitError on 429 response."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            status_code=429,
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(BrevoRateLimitError) as exc_info:
            brevo_client.send_email(
                to=[{"email": "test@example.com"}],
                subject="Test",
                html_content="<p>Test</p>",
                sender={"email": "sender@example.com"},
            )

        assert exc_info.value.status_code == 429

    def test_send_email_generic_api_error(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should raise BrevoAPIError on other error responses."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            status_code=500,
            json={"message": "Internal server error"},
        )

        with pytest.raises(BrevoAPIError) as exc_info:
            brevo_client.send_email(
                to=[{"email": "test@example.com"}],
                subject="Test",
                html_content="<p>Test</p>",
                sender={"email": "sender@example.com"},
            )

        assert exc_info.value.status_code == 500


class TestSendTemplateEmail:
    """Tests for the send_template_email method."""

    def test_send_template_email_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
        brevo_success_response: dict,
    ) -> None:
        """Successful template email send should return message ID."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        result = brevo_client.send_template_email(
            to=[{"email": "recipient@example.com"}],
            template_id=12,
            params={"firstName": "David"},
        )

        assert "messageId" in result

    def test_send_template_email_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
        brevo_success_response: dict,
    ) -> None:
        """Template email should build the correct API payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        brevo_client.send_template_email(
            to=[{"email": "recipient@example.com"}],
            template_id=42,
            params={"firstName": "David", "orderTotal": "$99"},
        )

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload["to"] == [{"email": "recipient@example.com"}]
        assert payload["templateId"] == 42
        assert payload["params"] == {"firstName": "David", "orderTotal": "$99"}


class TestSandboxMode:
    """Tests for sandbox mode functionality."""

    def test_sandbox_mode_adds_header(
        self,
        httpx_mock: HTTPXMock,
        brevo_success_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sandbox mode should add X-Sib-Sandbox header to payload."""
        # Enable sandbox mode
        monkeypatch.setattr(
            "dj_brevo.services.client.brevo_settings",
            type(
                "FakeSettings",
                (),
                {
                    "API_KEY": "test-key",
                    "API_BASE_URL": "https://api.brevo.com/v3",
                    "TIMEOUT": 10,
                    "SANDBOX": True,
                    "DEFAULT_FROM_EMAIL": "test@example.com",
                },
            )(),
        )

        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        client = BrevoClient(api_key="test-key")
        client.send_email(
            to=[{"email": "recipient@example.com"}],
            subject="Test",
            html_content="<p>Test</p>",
            sender={"email": "sender@example.com"},
        )

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert "headers" in payload
        assert payload["headers"] == {"X-Sib-Sandbox": "drop"}

    def test_sandbox_mode_disabled_no_header(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
        brevo_success_response: dict,
    ) -> None:
        """When sandbox is disabled, no sandbox header should be added."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/smtp/email",
            json=brevo_success_response,
        )

        brevo_client.send_email(
            to=[{"email": "recipient@example.com"}],
            subject="Test",
            html_content="<p>Test</p>",
            sender={"email": "sender@example.com"},
        )

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert "headers" not in payload
