"""Custom exceptions for dj_brevo."""

from typing import Any


class BrevoError(Exception):
    """Base exception for all dj_brevo errors."""

    pass


class BrevoAPIError(BrevoError):
    """Error returned by the Brevo API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class BrevoAuthError(BrevoAPIError):
    """Authentication failed - invalid or missing API key."""

    pass


class BrevoRateLimitError(BrevoAPIError):
    """Rate limit exceeded."""

    pass


class BrevoConfigError(BrevoError):
    """Configuration error - missing or invalid settings."""

    pass
