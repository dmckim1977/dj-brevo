"""Tests for Django admin classes and actions."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from dj_brevo.admin import (
    BrevoAttributeAdmin,
    BrevoContactAdmin,
    BrevoListAdmin,
)
from dj_brevo.models import BrevoAttribute, BrevoContact, BrevoList


@pytest.fixture
def admin_site() -> AdminSite:
    return AdminSite()


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def mock_request(request_factory: RequestFactory) -> MagicMock:
    request = request_factory.get("/admin/")
    request._messages = MagicMock()
    return request


class TestBrevoListAdmin:
    """Tests for BrevoListAdmin."""

    @pytest.mark.django_db
    def test_sync_to_brevo_creates_new_list(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo creates list in Brevo when brevo_id is None."""
        brevo_list = BrevoList.objects.create(
            name="Test List", slug="test-list", folder_id=1
        )
        admin = BrevoListAdmin(BrevoList, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_list.return_value = {"id": 123}

            queryset = BrevoList.objects.filter(pk=brevo_list.pk)
            admin.sync_to_brevo(mock_request, queryset)

            mock_client.create_list.assert_called_once_with(
                name="Test List", folder_id=1
            )

        brevo_list.refresh_from_db()
        assert brevo_list.brevo_id == 123
        assert brevo_list.synced_at is not None

    @pytest.mark.django_db
    def test_sync_to_brevo_updates_existing_list(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo updates list in Brevo when brevo_id exists."""
        brevo_list = BrevoList.objects.create(
            name="Test List", slug="test-list", folder_id=1, brevo_id=456
        )
        admin = BrevoListAdmin(BrevoList, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value

            queryset = BrevoList.objects.filter(pk=brevo_list.pk)
            admin.sync_to_brevo(mock_request, queryset)

            mock_client.update_list.assert_called_once_with(
                list_id=456, name="Test List", folder_id=1
            )

    @pytest.mark.django_db
    def test_sync_to_brevo_skips_without_folder_id(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo skips lists without folder_id."""
        brevo_list = BrevoList.objects.create(
            name="Test List", slug="test-list", folder_id=None
        )
        admin = BrevoListAdmin(BrevoList, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value

            queryset = BrevoList.objects.filter(pk=brevo_list.pk)
            admin.sync_to_brevo(mock_request, queryset)

            mock_client.create_list.assert_not_called()
            mock_client.update_list.assert_not_called()

    @pytest.mark.django_db
    def test_pull_from_brevo_creates_lists(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test pull_from_brevo creates new local lists from Brevo."""
        admin = BrevoListAdmin(BrevoList, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_lists.return_value = {
                "lists": [
                    {"id": 100, "name": "Newsletter", "folderId": 1},
                    {"id": 101, "name": "Promotions", "folderId": 2},
                ]
            }

            admin.pull_from_brevo(mock_request, BrevoList.objects.none())

        assert BrevoList.objects.count() == 2
        newsletter = BrevoList.objects.get(brevo_id=100)
        assert newsletter.name == "Newsletter"
        assert newsletter.folder_id == 1


class TestBrevoAttributeAdmin:
    """Tests for BrevoAttributeAdmin."""

    @pytest.mark.django_db
    def test_sync_to_brevo_creates_attribute(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo creates attribute in Brevo."""
        attr = BrevoAttribute.objects.create(
            name="FIRSTNAME", attribute_type="text", category="normal"
        )
        admin = BrevoAttributeAdmin(BrevoAttribute, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value

            admin.sync_to_brevo(mock_request, BrevoAttribute.objects.filter(pk=attr.pk))

            mock_client.create_attribute.assert_called_once()

        attr.refresh_from_db()
        assert attr.brevo_synced is True
        assert attr.synced_at is not None

    @pytest.mark.django_db
    def test_sync_to_brevo_skips_already_synced(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo skips already synced attributes."""
        attr = BrevoAttribute.objects.create(
            name="FIRSTNAME",
            attribute_type="text",
            category="normal",
            brevo_synced=True,
        )
        admin = BrevoAttributeAdmin(BrevoAttribute, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value

            admin.sync_to_brevo(mock_request, BrevoAttribute.objects.filter(pk=attr.pk))

            mock_client.create_attribute.assert_not_called()


class TestBrevoContactAdmin:
    """Tests for BrevoContactAdmin."""

    @pytest.mark.django_db
    def test_sync_to_brevo_creates_contact(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test sync_to_brevo creates contact in Brevo."""
        contact = BrevoContact.objects.create(
            email="test@example.com", attributes={"FIRSTNAME": "Test"}
        )
        admin = BrevoContactAdmin(BrevoContact, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_contact.return_value = {"id": 789}

            admin.sync_to_brevo(
                mock_request, BrevoContact.objects.filter(pk=contact.pk)
            )

            mock_client.create_contact.assert_called_once()

        contact.refresh_from_db()
        assert contact.brevo_id == 789
        assert contact.synced_at is not None

    @pytest.mark.django_db
    def test_pull_from_brevo_updates_contact(
        self, admin_site: AdminSite, mock_request: MagicMock
    ) -> None:
        """Test pull_from_brevo updates contact from Brevo."""
        contact = BrevoContact.objects.create(email="test@example.com", attributes={})
        admin = BrevoContactAdmin(BrevoContact, admin_site)

        with patch("dj_brevo.admin.BrevoClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_contact.return_value = {
                "id": 999,
                "attributes": {"FIRSTNAME": "Updated"},
            }

            admin.pull_from_brevo(
                mock_request, BrevoContact.objects.filter(pk=contact.pk)
            )

        contact.refresh_from_db()
        assert contact.brevo_id == 999
        assert contact.attributes == {"FIRSTNAME": "Updated"}
