"""Django email backend for Brevo."""

from collections.abc import Sequence

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

from dj_brevo.services import BrevoClient


class BrevoEmailBackend(BaseEmailBackend):
    """Django email backend that sends emails via Brevo API.

    Usage:
    # settings.py
    EMAIL_BACKEND = "dj_brevo.backends.BrevoEmailBackend"

    # Then user Django's normal email functions:
    from django.core.mail import send_mail
    send_mail("Subject", "Body", "from@example.com", ["to@example.com"])
    """

    def __init__(self, api_key: str | None = None, fail_silently: bool = False) -> None:
        """Initialize the backend.

        Args:
            api_key: Optional Brevo API Key (defaults to settings).
            fail_silently: If True, suppress exceptions on send failure.
        """
        super().__init__(fail_silently=fail_silently)
        self.api_key = api_key
        self._client: BrevoClient | None = None

    @property
    def client(self) -> BrevoClient:
        """Lazy load Brevo client."""
        if self._client is None:
            self._client = BrevoClient(api_key=self.api_key)
        return self._client

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        """Send one or more EmailMessage objects via Brevo.

        Args:
            email_messages: List of Django EmailMessage objects.

        Returns:
            Number of messages sent successfully.
        """
        if not email_messages:
            return 0

        sent_count = 0

        for message in email_messages:
            try:
                if self._send_message(message):
                    sent_count += 1
            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count

    def _send_message(self, message: EmailMessage) -> bool:
        """Send a single EmailMessage via Brevo.

        Args:
            message: Django EmailMessage object.

        Returns:
            True if sent successfully.
        """
        # Convert Django's recipient format to Brevo's format
        to = [{"email": email} for email in message.to]
        cc = [{"email": email} for email in message.cc] if message.cc else None
        bcc = [{"email": email} for email in message.bcc] if message.bcc else None
        reply_to = {"email": message.reply_to[0]} if message.reply_to else None

        # Build sender dict
        sender = {"email": message.from_email} if message.from_email else None

        # Get HTML content if available
        html_content = self._get_html_content(message)

        # Send via our client
        self.client.send_email(
            to=to,
            subject=str(message.subject),
            html_content=html_content or f"<pre>{message.body}</pre>",
            text_content=str(message.body),
            sender=sender,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )

        return True

    def _get_html_content(self, message: EmailMessage) -> str | None:
        """Extract HTML content from an EmailMessage.

        Args:
            message: Django EmailMessage object.

        Returns:
            HTML string if available, None otherwise.
        """
        # Check if this is an EmailMultiAlternatives with HTML
        alternatives = getattr(message, "alternatives", [])

        for content, mimetype in alternatives:
            if mimetype == "text/html":
                return str(content)

        return None
