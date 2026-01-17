from django.conf import settings
from django.db import models

from .base import BrevoSyncMixin
from .lists import BrevoList


class BrevoContact(BrevoSyncMixin):
    email = models.EmailField(unique=True)
    brevo_id = models.PositiveBigIntegerField(
        unique=True, null=True, blank=True, help_text="The contact ID in Brevo"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="brevo_contact",
    )
    attributes = models.JSONField(
        default=dict, blank=True, help_text="Contact attributes as key-value pairs."
    )
    lists = models.ManyToManyField(  # type: ignore[var-annotated]
        BrevoList,
        through="BrevoListMembership",
        related_name="contacts",
    )

    class Meta:
        verbose_name = "Brevo Contact"
        verbose_name_plural = "Brevo Contacts"

    def __str__(self) -> str:
        return self.email


class BrevoListMembership(BrevoSyncMixin):
    contact = models.ForeignKey(
        BrevoContact,
        on_delete=models.CASCADE,
        related_name="list_memberships",
    )
    list = models.ForeignKey(
        BrevoList,
        on_delete=models.CASCADE,
        related_name="contact_memberships",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Brevo List Membership"
        verbose_name_plural = "Brevo List Memberships"
        unique_together = [("contact", "list")]

    def __str__(self) -> str:
        return f"{self.contact} in {self.list}"
