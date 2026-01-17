from typing import Any, Literal, cast

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from dj_brevo.models import BrevoAttribute, BrevoList
from dj_brevo.services import BrevoClient
from dj_brevo.settings import brevo_settings

# Type aliases for Brevo API Literal types
AttributeCategory = Literal[
    "normal", "transactional", "category", "calculated", "global"
]
AttributeType = Literal[
    "text", "date", "float", "boolean", "id", "category", "multiple-choice", "user"
]


@receiver(post_save, sender=BrevoList)
def sync_brevo_list(
    sender: type[BrevoList],
    instance: BrevoList,
    created: bool,
    **kwargs: Any,
) -> None:
    """Trigger sync BrevoList >> Brevo on save."""
    # Skip if auto-sync is disabled
    if not brevo_settings.AUTO_SYNC:
        return

    # Skip if already syncing
    if getattr(instance, "_syncing", False):
        return

    client = BrevoClient()

    if instance.brevo_id is None:
        # Create new list in Brevo
        if instance.folder_id is None:
            return

        response = client.create_list(
            name=instance.name,
            folder_id=instance.folder_id,
        )

        # Save the returned brevo_id
        instance._syncing = True
        instance.brevo_id = response["id"]
        instance.synced_at = timezone.now()
        instance.save(update_fields=["brevo_id", "synced_at"])
        instance._syncing = False
    else:
        # Update existing list in Brevo
        client.update_list(
            list_id=instance.brevo_id,
            name=instance.name,
            folder_id=instance.folder_id,
        )
        instance._syncing = True
        instance.synced_at = timezone.now()
        instance.save(update_fields=["synced_at"])
        instance._syncing = False


@receiver(post_save, sender=BrevoAttribute)
def sync_brevo_attribute(
    sender: type[BrevoAttribute],
    instance: BrevoAttribute,
    created: bool,
    **kwargs: Any,
) -> None:
    """Sync BrevoAttribute >> Brevo on save"""
    # Skip if auto-sync is disabled
    if not brevo_settings.AUTO_SYNC:
        return

    # Skip if already synced to Brevo
    if instance.brevo_synced:
        return

    # Skip if already syncing
    if getattr(instance, "_syncing", False):
        return

    client = BrevoClient()

    # Build enumeration from options if category type
    enumeration = None
    if instance.attribute_type == "category":
        enumeration = [
            {"value": opt.value, "label": opt.label} for opt in instance.options.all()
        ]

    # Build multi_category_options if multiple-choice type
    multi_category_options = None
    if instance.attribute_type == "multiple-choice":
        multi_category_options = list(instance.options.values_list("label", flat=True))

    client.create_attribute(
        attribute_name=instance.name,
        attribute_category=cast(AttributeCategory, instance.category),
        attribute_type=cast(AttributeType, instance.attribute_type),
        enumeration=enumeration,
        multi_category_options=multi_category_options,
    )

    # Mark as synced
    instance._syncing = True
    instance.brevo_synced = True
    instance.synced_at = timezone.now()
    instance.save(update_fields=["brevo_synced", "synced_at"])
    instance._syncing = False
