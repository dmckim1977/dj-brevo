# Django + Brevo for transactional emails and customer journey automations."

## Installation

```bash
pip install dj-brevo

Quick Start

1. Add to your INSTALLED_APPS:

INSTALLED_APPS = [
    ...
    "dj_brevo",
]

2. Configure your Brevo API key:

DJ_BREVO = {
    "API_KEY": "your-brevo-api-key",
    "DEFAULT_FROM_EMAIL": "noreply@yourdomain.com",
}

3. Set the email backend:

EMAIL_BACKEND = "dj_brevo.backends.BrevoEmailBackend"

4. Send emails using Django's standard email functions:

from django.core.mail import send_mail

send_mail(
    subject="Welcome!",
    message="Thanks for signing up.",
    from_email="hello@yourdomain.com",
    recipient_list=["user@example.com"],
)

Using Brevo Templates

To send emails using templates created in Brevo's dashboard:

from dj_brevo.services import BrevoClient

client = BrevoClient()
client.send_template_email(
    to=[{"email": "user@example.com", "name": "David"}],
    template_id=12,
    params={"firstName": "David", "orderTotal": "$50"},
)

Configuration

All settings are optional except API_KEY:

DJ_BREVO = {
    # Required
    "API_KEY": "your-brevo-api-key",

    # Optional
    "DEFAULT_FROM_EMAIL": "noreply@yourdomain.com",
    "TIMEOUT": 10,  # Request timeout in seconds
    "API_BASE_URL": "https://api.brevo.com/v3",  # Override for testing
}

Requirements

- Python 3.12+
- Django 5.0+

License

MIT
