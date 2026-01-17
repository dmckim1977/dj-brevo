"""Tests for signal handlers."""

from unittest.mock import patch

import pytest

from dj_brevo.models import BrevoAttribute, BrevoList


@pytest.mark.django_db
class TestBrevoListSignal:
    """Tests for BrevoList post_save signal."""

    def test_auto_sync_disabled_skips_api_call(self, settings) -> None:
        """Should not call API when AUTO_SYNC is False."""
        settings.DJ_BREVO["AUTO_SYNC"] = False  # Explicitly set

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            BrevoList.objects.create(name="Test List", folder_id=1)

            mock_client.assert_not_called()

    def test_auto_sync_creates_list_in_brevo(self, settings) -> None:
        """Should call create_list when brevo_id is None."""
        settings.DJ_BREVO["AUTO_SYNC"] = True

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.create_list.return_value = {"id": 12345}

            brevo_list = BrevoList.objects.create(name="Test List", folder_id=1)

            mock_instance.create_list.assert_called_once_with(
                name="Test List",
                folder_id=1,
            )

            # Refresh from DB to get updated values
            brevo_list.refresh_from_db()
            assert brevo_list.brevo_id == 12345
            assert brevo_list.synced_at is not None

    def test_auto_sync_updates_list_in_brevo(self, settings) -> None:
        """Should call update_list when brevo_id exists."""
        settings.DJ_BREVO["AUTO_SYNC"] = True

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.create_list.return_value = {"id": 12345}

            # Create first (this will set brevo_id)
            brevo_list = BrevoList.objects.create(name="Test List", folder_id=1)

            # Reset mock to check update call
            mock_instance.reset_mock()

            # Update the list
            brevo_list.name = "Updated Name"
            brevo_list.save()

            mock_instance.update_list.assert_called_once_with(
                list_id=12345,
                name="Updated Name",
                folder_id=1,
            )

    def test_no_folder_id_skips_sync(self, settings) -> None:
        """Should skip sync if folder_id is None."""
        settings.DJ_BREVO["AUTO_SYNC"] = True

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            BrevoList.objects.create(name="Test List")  # No folder_id

            mock_client.return_value.create_list.assert_not_called()


@pytest.mark.django_db
class TestBrevoAttributeSignal:
    """Tests for BrevoAttribute post_save signal."""

    def test_auto_sync_disabled_skips_api_call(self, settings) -> None:
        """Should not call API when AUTO_SYNC is False."""
        settings.DJ_BREVO["AUTO_SYNC"] = False  # Explicitly set

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            BrevoAttribute.objects.create(name="TEST_ATTR")

            mock_client.assert_not_called()

    def test_auto_sync_creates_attribute_in_brevo(self, settings) -> None:
        """Should call create_attribute and mark as synced."""
        settings.DJ_BREVO["AUTO_SYNC"] = True

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            mock_instance = mock_client.return_value

            attr = BrevoAttribute.objects.create(
                name="MRR",
                attribute_type="float",
                category="normal",
            )

            mock_instance.create_attribute.assert_called_once()

            # Refresh and check synced
            attr.refresh_from_db()
            assert attr.brevo_synced is True
            assert attr.synced_at is not None

    def test_already_synced_skips_api_call(self, settings) -> None:
        """Should not call API if already synced."""
        settings.DJ_BREVO["AUTO_SYNC"] = True

        with patch("dj_brevo.signals.handlers.BrevoClient") as mock_client:
            mock_instance = mock_client.return_value

            # Create (will sync)
            attr = BrevoAttribute.objects.create(name="TEST_ATTR")

            # Reset and save again
            mock_instance.reset_mock()
            attr.save()

            # Should not call API again
            mock_instance.create_attribute.assert_not_called()
