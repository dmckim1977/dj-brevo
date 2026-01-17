# dj-brevo

Django integration for Brevo (formerly Sendinblue) - transactional emails and contact management.

## Installation

```bash
pip install dj-brevo
```

## Quick Start

1. Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "dj_brevo",
]
```

2. Configure your Brevo API key:

```python
DJ_BREVO = {
    "API_KEY": "your-brevo-api-key",
    "DEFAULT_FROM_EMAIL": "noreply@yourdomain.com",
}
```

3. Run migrations:

```bash
python manage.py migrate dj_brevo
```

4. Set the email backend (optional):

```python
EMAIL_BACKEND = "dj_brevo.backends.BrevoEmailBackend"
```

## Sending Emails

### Using Django's Email Functions

```python
from django.core.mail import send_mail

send_mail(
    subject="Welcome!",
    message="Thanks for signing up.",
    from_email="hello@yourdomain.com",
    recipient_list=["user@example.com"],
)
```

### Using Brevo Templates

Send emails using templates created in Brevo's dashboard:

```python
from dj_brevo.services import BrevoClient

client = BrevoClient()
client.send_template_email(
    to=[{"email": "user@example.com", "name": "David"}],
    template_id=12,
    params={"firstName": "David", "orderTotal": "$50"},
)
```

## Contact Management

### Models

dj-brevo provides Django models for managing Brevo contacts, lists, and attributes locally:

```python
from dj_brevo.models import BrevoContact, BrevoList, BrevoAttribute

# Create a contact
contact = BrevoContact.objects.create(
    email="user@example.com",
    attributes={"FIRSTNAME": "David", "MRR": 99.99},
)

# Create a list (auto-syncs to Brevo when AUTO_SYNC=True)
newsletter = BrevoList.objects.create(
    name="Newsletter",
    folder_id=1,  # Required for Brevo sync
)

# Add contact to list
contact.lists.add(newsletter)

# Create an attribute (auto-syncs to Brevo when AUTO_SYNC=True)
attr = BrevoAttribute.objects.create(
    name="SUBSCRIPTION_STATUS",
    attribute_type="text",
    category="normal",
)
```

### Auto-Sync

When `AUTO_SYNC` is enabled (default), `BrevoList` and `BrevoAttribute` models automatically sync to Brevo on save:

- **BrevoList**: Creates/updates the list in Brevo, stores the returned `brevo_id`
- **BrevoAttribute**: Creates the attribute in Brevo, marks `brevo_synced=True`

Contacts do **not** auto-sync - use the API client directly for contact operations.

### Direct API Access

For full control, use the `BrevoClient` directly:

```python
from dj_brevo.services import BrevoClient

client = BrevoClient()

# Contacts
client.create_contact(email="user@example.com", attributes={"FIRSTNAME": "David"})
client.get_contact("user@example.com")
client.update_contact(identifier="user@example.com", attributes={"MRR": 150})

# Lists
client.get_lists()
client.create_list(name="Newsletter", folder_id=1)
client.add_contacts_to_list(list_id=5, emails=["user@example.com"])
client.remove_contacts_from_list(list_id=5, emails=["user@example.com"])

# Attributes
client.get_attributes()
client.create_attribute(
    attribute_name="MRR",
    attribute_type="float",
    attribute_category="normal",
)
```

## Configuration

All settings are optional except `API_KEY`:

```python
DJ_BREVO = {
    # Required
    "API_KEY": "your-brevo-api-key",

    # Optional
    "DEFAULT_FROM_EMAIL": "noreply@yourdomain.com",
    "TIMEOUT": 10,  # Request timeout in seconds
    "API_BASE_URL": "https://api.brevo.com/v3",  # Override for testing
    "SANDBOX": False,  # Enable sandbox mode for testing
    "AUTO_SYNC": True,  # Auto-sync lists/attributes to Brevo on save
}
```

### Disabling Auto-Sync

To manually control when data syncs to Brevo:

```python
DJ_BREVO = {
    "API_KEY": "your-brevo-api-key",
    "AUTO_SYNC": False,
}
```

This is recommended for tests to prevent API calls.

## Sandbox Mode

Use sandbox mode to test your integration without sending actual emails:

```python
DJ_BREVO = {
    "API_KEY": "your-brevo-api-key",
    "SANDBOX": True,  # Emails won't be sent
}
```

In sandbox mode:
- No emails are sent to recipients
- No email logs are created in your Brevo account
- You receive a success response with a `messageId` confirming the API is working

This is useful for automated testing and CI/CD pipelines.

## Requirements

- Python 3.12+
- Django 5.0+

## License

MIT
