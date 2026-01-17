"""Base classes for dj-brevo models."""

from django.db import models


class BrevoSyncMixin(models.Model):
    """Abstract mixin for models that sync with Brevo.

    Provides common fields for tracking sync state.
    """

    synced_at = models.DateTimeField(
        null=True, blank=True, help_text="When this record was last synced with Brevo."
    )
    _syncing: bool = False

    class Meta:
        abstract = True
