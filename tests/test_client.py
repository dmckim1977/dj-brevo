"""Tests for the Brevo API client."""

import re

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


class TestCreateContact:
    """Tests for the create_contact method."""

    def test_create_contact_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Successful contact creation should return contact ID."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts",
            json={"id": 123456},
        )

        result = brevo_client.create_contact(email="user@example.com")

        assert result["id"] == 123456

    def test_create_contact_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Create contact should build the correct API payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts",
            json={"id": 123456},
        )

        brevo_client.create_contact(
            email="user@example.com",
            attributes={"FIRSTNAME": "David", "LASTNAME": "Smith"},
            list_ids=[1, 2, 3],
            update_enabled=False,
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "POST"

        import json

        payload = json.loads(request.content)

        assert payload["email"] == "user@example.com"
        assert payload["attributes"] == {"FIRSTNAME": "David", "LASTNAME": "Smith"}
        assert payload["listIds"] == [1, 2, 3]
        assert payload["updateEnabled"] is False

    def test_create_contact_minimal_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Create contact with only email should have minimal payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts",
            json={"id": 123456},
        )

        brevo_client.create_contact(email="user@example.com")

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload == {"email": "user@example.com", "updateEnabled": True}


class TestGetContact:
    """Tests for the get_contact method."""

    def test_get_contact_by_email(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should retrieve contact by email."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/user@example.com",
            json={
                "id": 123456,
                "email": "user@example.com",
                "attributes": {"FIRSTNAME": "David"},
            },
        )

        result = brevo_client.get_contact("user@example.com")

        assert result["id"] == 123456
        assert result["email"] == "user@example.com"

    def test_get_contact_by_id(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should retrieve contact by numeric ID."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/123456",
            json={"id": 123456, "email": "user@example.com"},
        )

        result = brevo_client.get_contact(123456)

        assert result["id"] == 123456

    def test_get_contact_uses_get_method(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should use GET HTTP method."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/user@example.com",
            json={"id": 123456},
        )

        brevo_client.get_contact("user@example.com")

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "GET"


class TestUpdateContact:
    """Tests for the update_contact method."""

    def test_update_contact_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Successful contact update should return empty dict."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/user@example.com",
            json={},
        )

        result = brevo_client.update_contact(
            identifier="user@example.com",
            attributes={"FIRSTNAME": "Updated"},
        )

        assert result == {}

    def test_update_contact_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Update contact should build the correct API payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/123456",
            json={},
        )

        brevo_client.update_contact(
            identifier=123456,
            email="newemail@example.com",
            attributes={"FIRSTNAME": "David"},
            list_ids=[1, 2],
            unlink_list_ids=[3, 4],
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "PUT"

        import json

        payload = json.loads(request.content)

        assert payload["email"] == "newemail@example.com"
        assert payload["attributes"] == {"FIRSTNAME": "David"}
        assert payload["listIds"] == [1, 2]
        assert payload["unlinkListIds"] == [3, 4]


class TestListContacts:
    """Tests for the list_contacts method."""

    def test_list_contacts_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should return list of contacts."""
        httpx_mock.add_response(
            url=re.compile(r"https://api\.brevo\.com/v3/contacts(\?.*)?$"),
            json={
                "contacts": [
                    {"id": 1, "email": "a@example.com"},
                    {"id": 2, "email": "b@example.com"},
                ],
                "count": 2,
            },
        )

        result = brevo_client.list_contacts(list_ids=None)

        assert len(result["contacts"]) == 2
        assert result["count"] == 2

    def test_list_contacts_with_params(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should pass query parameters correctly."""
        httpx_mock.add_response(
            url=re.compile(r"https://api\.brevo\.com/v3/contacts\?"),
            json={"contacts": [], "count": 0},
        )

        brevo_client.list_contacts(
            list_ids=[1, 2],
            limit=25,
            offset=50,
            sort="asc",
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "GET"

        # Check query params
        assert "limit=25" in str(request.url)
        assert "offset=50" in str(request.url)
        assert "sort=asc" in str(request.url)


class TestAddContactsToList:
    """Tests for the add_contacts_to_list method."""

    def test_add_contacts_to_list_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should add contacts to list."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/5/contacts/add",
            json={"contacts": {"success": ["a@example.com", "b@example.com"]}},
        )

        result = brevo_client.add_contacts_to_list(
            list_id=5,
            emails=["a@example.com", "b@example.com"],
        )

        assert "contacts" in result

    def test_add_contacts_to_list_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should build correct payload with emails."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/5/contacts/add",
            json={},
        )

        brevo_client.add_contacts_to_list(
            list_id=5,
            emails=["a@example.com", "b@example.com"],
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "POST"

        import json

        payload = json.loads(request.content)

        assert payload == {"emails": ["a@example.com", "b@example.com"]}


class TestRemoveContactsFromList:
    """Tests for the remove_contacts_from_list method."""

    def test_remove_contacts_from_list_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should remove contacts from list."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/5/contacts/remove",
            json={"contacts": {"success": ["a@example.com"]}},
        )

        result = brevo_client.remove_contacts_from_list(
            list_id=5,
            emails=["a@example.com"],
        )

        assert "contacts" in result

    def test_remove_contacts_from_list_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should build correct payload with emails."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/5/contacts/remove",
            json={},
        )

        brevo_client.remove_contacts_from_list(
            list_id=5,
            emails=["a@example.com"],
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "POST"

        import json

        payload = json.loads(request.content)

        assert payload == {"emails": ["a@example.com"]}


class TestGetLists:
    """Tests for the get_lists method."""

    def test_get_lists_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should return list of contact lists."""
        httpx_mock.add_response(
            url=re.compile(r"https://api\.brevo\.com/v3/contacts/lists(\?.*)?$"),
            json={
                "lists": [
                    {"id": 1, "name": "Newsletter"},
                    {"id": 2, "name": "Customers"},
                ],
                "count": 2,
            },
        )

        result = brevo_client.get_lists()

        assert len(result["lists"]) == 2
        assert result["count"] == 2

    def test_get_lists_with_params(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should pass pagination parameters."""
        httpx_mock.add_response(
            url=re.compile(r"https://api\.brevo\.com/v3/contacts/lists\?"),
            json={"lists": [], "count": 0},
        )

        brevo_client.get_lists(limit=10, offset=20, sort="asc")

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "GET"

        assert "limit=10" in str(request.url)
        assert "offset=20" in str(request.url)
        assert "sort=asc" in str(request.url)


class TestCreateList:
    """Tests for the create_list method."""

    def test_create_list_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should create a list and return ID."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists",
            json={"id": 42},
        )

        result = brevo_client.create_list(name="New List", folder_id=1)

        assert result["id"] == 42

    def test_create_list_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should build correct payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists",
            json={"id": 42},
        )

        brevo_client.create_list(name="My List", folder_id=5)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "POST"

        import json

        payload = json.loads(request.content)

        assert payload == {"name": "My List", "folderId": 5}


class TestUpdateList:
    """Tests for the update_list method."""

    def test_update_list_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should update a list."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/42",
            json={},
        )

        result = brevo_client.update_list(list_id=42, name="Updated Name")

        assert result == {}

    def test_update_list_uses_put_method(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should use PUT HTTP method."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/42",
            json={},
        )

        brevo_client.update_list(list_id=42, name="New Name")

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "PUT"

    def test_update_list_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should only include provided fields in payload."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/42",
            json={},
        )

        brevo_client.update_list(list_id=42, folder_id=10)

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload == {"folderId": 10}
        assert "name" not in payload


class TestDeleteList:
    """Tests for the delete_list method."""

    def test_delete_list_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should delete a list."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/42",
            json={},
        )

        result = brevo_client.delete_list(list_id=42)

        assert result == {}

    def test_delete_list_uses_delete_method(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should use DELETE HTTP method."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/lists/42",
            json={},
        )

        brevo_client.delete_list(list_id=42)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "DELETE"


class TestGetAttributes:
    """Tests for the get_attributes method."""

    def test_get_attributes_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should return list of attributes."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes",
            json={
                "attributes": [
                    {"name": "FIRSTNAME", "category": "normal", "type": "text"},
                    {"name": "LASTNAME", "category": "normal", "type": "text"},
                ]
            },
        )

        result = brevo_client.get_attributes()

        assert len(result["attributes"]) == 2

    def test_get_attributes_uses_get_method(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should use GET HTTP method."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes",
            json={"attributes": []},
        )

        brevo_client.get_attributes()

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "GET"


class TestCreateAttribute:
    """Tests for the create_attribute method."""

    def test_create_attribute_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should create an attribute."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/SUBSCRIPTION_STATUS",
            json={},
        )

        result = brevo_client.create_attribute(
            attribute_name="SUBSCRIPTION_STATUS",
            attribute_category="normal",
            attribute_type="text",
        )

        assert result == {}

    def test_create_attribute_builds_correct_payload(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should build correct payload with type."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/MRR",
            json={},
        )

        brevo_client.create_attribute(
            attribute_name="MRR",
            attribute_category="normal",
            attribute_type="float",
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "POST"

        import json

        payload = json.loads(request.content)

        assert payload == {"type": "float"}

    def test_create_attribute_with_enumeration(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should include enumeration for category type."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/category/STATUS",
            json={},
        )

        brevo_client.create_attribute(
            attribute_name="STATUS",
            attribute_category="category",
            enumeration=[
                {"value": 1, "label": "Active"},
                {"value": 2, "label": "Churned"},
            ],
        )

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload["enumeration"] == [
            {"value": 1, "label": "Active"},
            {"value": 2, "label": "Churned"},
        ]

    def test_create_attribute_with_multi_category_options(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should include multiCategoryOptions for multiple-choice type."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/PRODUCTS",
            json={},
        )

        brevo_client.create_attribute(
            attribute_name="PRODUCTS",
            attribute_category="normal",
            attribute_type="multiple-choice",
            multi_category_options=["Product A", "Product B", "Product C"],
        )

        request = httpx_mock.get_request()
        assert request is not None

        import json

        payload = json.loads(request.content)

        assert payload["type"] == "multiple-choice"
        assert payload["multiCategoryOptions"] == [
            "Product A",
            "Product B",
            "Product C",
        ]

    def test_create_attribute_default_category(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should default to normal category."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/TEST",
            json={},
        )

        brevo_client.create_attribute(
            attribute_name="TEST",
            attribute_type="text",
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert "/normal/TEST" in str(request.url)


class TestDeleteAttribute:
    """Tests for the delete_attribute method."""

    def test_delete_attribute_success(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should delete an attribute."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/OLD_ATTR",
            json={},
        )

        result = brevo_client.delete_attribute(
            attribute_name="OLD_ATTR",
            attribute_category="normal",
        )

        assert result == {}

    def test_delete_attribute_uses_delete_method(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should use DELETE HTTP method."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/normal/OLD_ATTR",
            json={},
        )

        brevo_client.delete_attribute(attribute_name="OLD_ATTR")

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "DELETE"

    def test_delete_attribute_different_category(
        self,
        httpx_mock: HTTPXMock,
        brevo_client: BrevoClient,
    ) -> None:
        """Should support different attribute categories."""
        httpx_mock.add_response(
            url="https://api.brevo.com/v3/contacts/attributes/transactional/ORDER_ID",
            json={},
        )

        brevo_client.delete_attribute(
            attribute_name="ORDER_ID",
            attribute_category="transactional",
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert "/transactional/ORDER_ID" in str(request.url)
