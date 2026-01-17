from django.db import models

from .base import BrevoSyncMixin


class BrevoAttribute(BrevoSyncMixin):
    class AttributeType(models.TextChoices):
        TEXT = "text", "Text"
        FLOAT = "float", "Float"
        DATE = "date", "Date"
        BOOLEAN = "boolean", "Boolean"
        CATEGORY = "category", "Category"
        MULTIPLE_CHOICE = "multiple-choice", "Multiple Choice"
        USER = "user", "User"

    class Category(models.TextChoices):
        NORMAL = "normal", "Normal"
        CATEGORY = "category", "Category"
        TRANSACTIONAL = "transactional", "Transactional"

    name = models.CharField(max_length=255, unique=True)
    attribute_type = models.CharField(
        max_length=20,
        choices=AttributeType.choices,
        default=AttributeType.TEXT,
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.NORMAL,
    )
    brevo_synced = models.BooleanField(
        default=False, help_text="If this attribute has been created in Brevo."
    )

    class Meta:
        verbose_name = "Brevo Attribute"
        verbose_name_plural = "Brevo Attributes"

    def __str__(self) -> str:
        return self.name


class BrevoAttributeOption(models.Model):
    attribute = models.ForeignKey(
        BrevoAttribute,
        on_delete=models.CASCADE,
        related_name="options",
    )
    value = models.IntegerField(
        null=True, blank=True, help_text="Numeric value for category-type attributes."
    )
    label = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Brevo Attribute Option"
        verbose_name_plural = "Brevo Attribute Options"
        unique_together = [("attribute", "label")]
        ordering = ["order"]

    def __str__(self) -> str:
        return self.label
