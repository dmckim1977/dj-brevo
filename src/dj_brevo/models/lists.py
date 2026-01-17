from typing import Any

from django.db import models
from django.utils.text import slugify

from .base import BrevoSyncMixin


class BrevoList(BrevoSyncMixin):
    brevo_id = models.PositiveBigIntegerField(
        unique=True, null=True, blank=True, help_text="The list ID in Brevo"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    folder_id = models.PositiveBigIntegerField(
        null=True, blank=True, help_text="Brevo folder ID containing this list."
    )

    class Meta:
        verbose_name = "Brevo List"
        verbose_name_plural = "Brevo Lists"

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
