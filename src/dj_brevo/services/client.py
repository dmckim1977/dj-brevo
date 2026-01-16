"""HTTP client for the Brevo API."""

from typing import Any

import httpx

from dj_brevo.exceptions import (
    BrevoAPIError,
    BrevoAuthError,
    BrevoConfigError,
    BrevoRateLimitError,
)
from dj_brevo.settings import brevo_settings


class BrevoClient:
    """Client for interacting with the Brevo API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the client.

        Args:
            api_key: Brevo API key. If not provided, reads from settings.
        """
        self.api_key = api_key or brevo_settings.API_KEY
        if not self.api_key:
            raise BrevoConfigError(
                "Brevo API key not configured."
                "Set DJ_BREVO['API_KEY'] in your Django settings"
            )
        self.base_url = brevo_settings.API_BASE_URL
        self.timeout = brevo_settings.TIMEOUT
        self.sandbox = brevo_settings.SANDBOX

    def _get_headers(self) -> dict[str, str]:
        """Returns headers required for Brevo API requests."""
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _apply_sandbox(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Add sandbox header to payload if sandbox mode is enabled.

        Args:
            payload: The API request payload.

        Returns:
            Payload with sandbox header added if enabled.
        """
        if self.sandbox:
            payload["headers"] = {"X-Sib-Sandbox": "drop"}
        return payload

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: The https response object.

        Returns:
            Parsed JSON response data.

        Raises:
            BrevoAuthError: If authentication failed (401).
            BrevoRateLimitError: If rate limit exceeded (429).
            BrevoAPIError: For other API errors (4xx, 5xx).
        """
        # Try to parse JSON
        try:
            data = response.json()
        except ValueError:
            data = {}

        # Success - return the data
        if response.is_success:
            return data  # type: ignore[no-any-return]

        # Map status codes to our exceptions
        message = data.get("message", response.text)

        if response.status_code == 401:
            raise BrevoAuthError(
                message=message,
                status_code=401,
                response_data=data,
            )
        elif response.status_code == 429:
            raise BrevoRateLimitError(
                message=message,
                status_code=429,
                response_data=data,
            )
        else:
            raise BrevoAPIError(
                message=message,
                status_code=response.status_code,
                response_data=data,
            )

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to the Brevo API.

        Args:
            endpoint: API endpoint path (e.g., "/smtp/email").
            payload: JSON payload to send.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.base_url}{endpoint}"

        response = httpx.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        return self._handle_response(response)

    def send_email(
        self,
        *,
        to: list[dict[str, str]],
        subject: str,
        html_content: str,
        sender: dict[str, str] | None = None,
        text_content: str | None = None,
        reply_to: dict[str, str] | None = None,
        cc: list[dict[str, str]] | None = None,
        bcc: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send an email with HTML content you provide.

        Args:
              to: List of recipients, e.g., [{"email": "a@b.com", "name": "Name"}]
              subject: Email subject line.
              html_content: Rendered HTML body.
              sender: Sender info. Defaults to DJ_BREVO["DEFAULT_FROM_EMAIL"].
              text_content: Plain text version (optional).
              reply_to: Reply-to address (optional).
              cc: CC recipients (optional).
              bcc: BCC recipients (optional).

        Returns:
            API response with messageId.

        Example:
            client.send_email(
                to=[{"email": "user@example.com", "name": "David"}],
                subject="Welcome!",
                html_content="<html><body>Hello!</body></html>",
            )

        """
        if sender is None:
            default_email = brevo_settings.DEFAULT_FROM_EMAIL
            if not default_email:
                raise BrevoConfigError(
                    "No sender provided and DJ_BREVO['DEFAULT_FROM_EMAIL'] not set."
                )
            sender = {"email": default_email}

        payload: dict[str, Any] = {
            "sender": sender,
            "to": to,
            "subject": subject,
            "htmlContent": html_content,
        }

        if text_content:
            payload["textContent"] = text_content
        if reply_to:
            payload["replyTo"] = reply_to
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        return self._post("/smtp/email", self._apply_sandbox(payload))

    def send_template_email(
        self,
        *,
        to: list[dict[str, str]],
        template_id: int,
        params: dict[str, Any] | None = None,
        sender: dict[str, str] | None = None,
        reply_to: dict[str, str] | None = None,
        cc: list[dict[str, str]] | None = None,
        bcc: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send an email using a Brevo template.

        Args:
            to: List of recipients, e.g., [{"email": "a@b.com", "name": "Name"}]
            template_id: ID of the template in Brevo.
            params: Template variables, e.g., {"firstName": "David"}.
            sender: Sender info (optional, can be set in Brevo template).
            reply_to: Reply-to address (optional).
            cc: CC recipients (optional).
            bcc: BCC recipients (optional).

        Returns:
            API response with messageId.

        Example:
            client.send_template_email(
                to=[{"email": "user@example.com"}],
                template_id=12,
                params={"firstName": "David", "orderTotal": "$50"},
            )
        """
        payload: dict[str, Any] = {
            "to": to,
            "templateId": template_id,
        }

        if params:
            payload["params"] = params
        if sender:
            payload["sender"] = sender
        if reply_to:
            payload["replyTo"] = reply_to
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        return self._post("/smtp/email", self._apply_sandbox(payload))
