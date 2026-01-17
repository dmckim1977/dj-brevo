import pytest

from dj_brevo.models import (
    BrevoAttribute,
    BrevoAttributeOption,
    BrevoContact,
    BrevoList,
    BrevoListMembership,
)


@pytest.mark.django_db
class TestBrevoList:
    """Tests for the BrevoList model."""

    def test_create_list(self) -> None:
        """Should create a list with auto-generated slug."""
        brevo_list = BrevoList.objects.create(name="My Newsletter")

        assert brevo_list.name == "My Newsletter"
        assert brevo_list.slug == "my-newsletter"
        assert brevo_list.brevo_id is None
        assert brevo_list.synced_at is None

    def test_slug_not_overwritten(self) -> None:
        """Should not overwrite slug if already set."""
        brevo_list = BrevoList.objects.create(
            name="My Newsletter",
            slug="custom-slug",
        )

        assert brevo_list.slug == "custom-slug"

    def test_str(self) -> None:
        """Should return name as string representation."""
        brevo_list = BrevoList(name="Test List")
        assert str(brevo_list) == "Test List"


@pytest.mark.django_db
class TestBrevoAttribute:
    """Tests for the BrevoAttribute model."""

    def test_create_attribute(self) -> None:
        """Should create an attribute with defaults."""
        attr = BrevoAttribute.objects.create(name="FIRSTNAME")

        assert attr.name == "FIRSTNAME"
        assert attr.attribute_type == "text"
        assert attr.category == "normal"
        assert attr.brevo_synced is False

    def test_attribute_with_options(self) -> None:
        """Should create attribute with options."""
        attr = BrevoAttribute.objects.create(
            name="STATUS",
            attribute_type="category",
            category="category",
        )
        BrevoAttributeOption.objects.create(
            attribute=attr,
            value=1,
            label="Active",
            order=0,
        )
        BrevoAttributeOption.objects.create(
            attribute=attr,
            value=2,
            label="Churned",
            order=1,
        )

        assert attr.options.count() == 2
        labels = list(attr.options.values_list("label", flat=True))
        assert labels == ["Active", "Churned"]


@pytest.mark.django_db
class TestBrevoContact:
    """Tests for the BrevoContact model."""

    def test_create_contact(self) -> None:
        """Should create a contact."""
        contact = BrevoContact.objects.create(email="user@example.com")

        assert contact.email == "user@example.com"
        assert contact.brevo_id is None
        assert contact.user is None
        assert contact.attributes == {}

    def test_contact_with_attributes(self) -> None:
        """Should store attributes as JSON."""
        contact = BrevoContact.objects.create(
            email="user@example.com",
            attributes={"FIRSTNAME": "David", "MRR": 99.99},
        )

        assert contact.attributes["FIRSTNAME"] == "David"
        assert contact.attributes["MRR"] == 99.99

    def test_contact_list_membership(self) -> None:
        """Should add contact to list via membership."""
        contact = BrevoContact.objects.create(email="user@example.com")
        brevo_list = BrevoList.objects.create(name="Newsletter")

        membership = BrevoListMembership.objects.create(
            contact=contact,
            list=brevo_list,
        )

        assert contact.lists.count() == 1
        assert contact.lists.first() == brevo_list
        assert membership.added_at is not None
        assert membership.synced_at is None
