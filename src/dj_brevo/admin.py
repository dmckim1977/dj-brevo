from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from dj_brevo.models import (
    BrevoAttribute,
    BrevoAttributeOption,
    BrevoContact,
    BrevoList,
    BrevoListMembership,
)
from dj_brevo.services import BrevoClient


@admin.register(BrevoList)
class BrevoListAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for managing Brevo contact lists."""

    list_display = ["name", "slug", "brevo_id", "folder_id", "synced_at"]
    list_filter = ["synced_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["brevo_id", "synced_at"]
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = [
        (None, {"fields": ["name", "slug", "folder_id"]}),
        ("Brevo Sync", {"fields": ["brevo_id", "synced_at"]}),
    ]

    actions = ["sync_to_brevo", "pull_from_brevo"]

    @admin.action(description="Sync selected lists to Brevo")
    def sync_to_brevo(
        self,
        request: HttpRequest,
        queryset: QuerySet[BrevoList],
    ) -> None:
        client = BrevoClient()
        synced = 0
        for obj in queryset:
            if obj.folder_id is None:
                self.message_user(
                    request,
                    f"Skipped '{obj.name}' - no folder_id set",
                    messages.WARNING,
                )
                continue

            if obj.brevo_id is None:
                response = client.create_list(
                    name=obj.name,
                    folder_id=obj.folder_id,
                )
                obj.brevo_id = response["id"]
            else:
                client.update_list(
                    list_id=obj.brevo_id,
                    name=obj.name,
                    folder_id=obj.folder_id,
                )
            obj.synced_at = timezone.now()
            obj._syncing = True
            obj.save(update_fields=["brevo_id", "synced_at"])
            obj._syncing = False
            synced += 1

        self.message_user(request, f"Synced {synced} list(s) to Brevo")

    @admin.action(description="Pull all lists from Brevo")
    def pull_from_brevo(
        self, request: HttpRequest, queryset: QuerySet[BrevoList]
    ) -> None:
        """Pull all lists from Brevo, creating/updating local records."""
        client = BrevoClient()
        response = client.get_lists(limit=50)

        created = 0
        updated = 0
        for item in response.get("lists", []):
            obj, was_created = BrevoList.objects.update_or_create(
                brevo_id=item["id"],
                defaults={
                    "name": item["name"],
                    "folder_id": item.get("folderId"),
                    "synced_at": timezone.now(),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(
            request, f"Pulled from Brevo: {created} created, {updated} updated."
        )


class BrevoAttributeOptionInline(admin.TabularInline):  # type: ignore[type-arg]
    """Inline for attribute options (category/multiple-choice values)."""

    model = BrevoAttributeOption
    extra = 1
    fields = ["label", "value", "order"]


@admin.register(BrevoAttribute)
class BrevoAttributeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for managing Brevo contact attributes."""

    list_display = ["name", "attribute_type", "category", "brevo_synced", "synced_at"]
    list_filter = ["attribute_type", "category", "brevo_synced"]
    search_fields = ["name"]
    readonly_fields = ["brevo_synced", "synced_at"]

    fieldsets = [
        (None, {"fields": ["name", "attribute_type", "category"]}),
        ("Brevo Sync", {"fields": ["brevo_synced", "synced_at"]}),
    ]

    inlines = [BrevoAttributeOptionInline]

    actions = ["sync_to_brevo", "pull_from_brevo"]

    @admin.action(description="Sync selected attributes to Brevo")
    def sync_to_brevo(
        self, request: HttpRequest, queryset: QuerySet[BrevoAttribute]
    ) -> None:
        client = BrevoClient()
        synced = 0
        for obj in queryset:
            if obj.brevo_synced:
                continue  # Already synced

            # Build enumeration for category type
            enumeration = None
            if obj.attribute_type == "category":
                enumeration = [
                    {"value": opt.value, "label": opt.label}
                    for opt in obj.options.all()
                ]

            # Build multi_category_options for multiple-choice type
            multi_category_options = None
            if obj.attribute_type == "multiple-choice":
                multi_category_options = list(
                    obj.options.values_list("label", flat=True)
                )

            client.create_attribute(
                attribute_name=obj.name,
                attribute_category=obj.category,  # type: ignore[arg-type]
                attribute_type=obj.attribute_type,  # type: ignore[arg-type]
                enumeration=enumeration,
                multi_category_options=multi_category_options,
            )

            obj.brevo_synced = True
            obj.synced_at = timezone.now()
            obj._syncing = True
            obj.save(update_fields=["brevo_synced", "synced_at"])
            obj._syncing = False
            synced += 1

        self.message_user(request, f"Synced {synced} attribute(s) to Brevo.")

    @admin.action(description="Pull all attributes from Brevo")
    def pull_from_brevo(
        self, request: HttpRequest, queryset: QuerySet[BrevoAttribute]
    ) -> None:
        """Pull all attributes from Brevo, creating/updating local records."""
        client = BrevoClient()
        response = client.get_attributes()

        created = 0
        updated = 0
        for category_data in response.get("attributes", []):
            category = category_data.get("category", "normal")
            for attr in category_data.get("attributes", []):
                # Map Brevo type to our type
                attr_type = attr.get("type", "text")

                obj, was_created = BrevoAttribute.objects.update_or_create(
                    name=attr["name"],
                    defaults={
                        "attribute_type": attr_type,
                        "category": category,
                        "brevo_synced": True,
                        "synced_at": timezone.now(),
                    },
                )

                # Handle enumeration (category type options)
                if attr_type == "category" and "enumeration" in attr:
                    for enum_item in attr["enumeration"]:
                        BrevoAttributeOption.objects.update_or_create(
                            attribute=obj,
                            label=enum_item["label"],
                            defaults={
                                "value": enum_item["value"],
                                "order": 0,
                            },
                        )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.message_user(
            request, f"Pulled from Brevo: {created} created, {updated} updated."
        )


class BrevoListMembershipInline(admin.TabularInline):  # type: ignore[type-arg]
    """Inline for contact list memberships."""

    model = BrevoListMembership
    extra = 1
    fields = ["list", "added_at", "synced_at"]
    readonly_fields = ["added_at", "synced_at"]
    autocomplete_fields = ["list"]


@admin.register(BrevoContact)
class BrevoContactAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for managing Brevo contacts."""

    list_display = ["email", "user", "brevo_id", "synced_at"]
    list_filter = ["synced_at"]
    search_fields = ["email", "user__email"]
    readonly_fields = ["brevo_id", "synced_at"]
    autocomplete_fields = ["user"]

    fieldsets = [
        (None, {"fields": ["email", "user", "attributes"]}),
        ("Brevo Sync", {"fields": ["brevo_id", "synced_at"]}),
    ]

    inlines = [BrevoListMembershipInline]

    actions = ["sync_to_brevo", "pull_from_brevo"]

    @admin.action(description="Sync selected contacts to Brevo")
    def sync_to_brevo(
        self, request: HttpRequest, queryset: QuerySet[BrevoContact]
    ) -> None:
        client = BrevoClient()
        synced = 0
        for obj in queryset:
            list_ids: list[int] = [
                bid
                for bid in obj.lists.filter(brevo_id__isnull=False).values_list(
                    "brevo_id", flat=True
                )
                if bid is not None
            ]

            if obj.brevo_id is None:
                response = client.create_contact(
                    email=obj.email,
                    attributes=obj.attributes,
                    list_ids=list_ids,
                )
                obj.brevo_id = response.get("id")
            else:
                client.update_contact(
                    identifier=obj.brevo_id,
                    attributes=obj.attributes,
                    list_ids=list_ids,
                )

            obj.synced_at = timezone.now()
            obj._syncing = True
            obj.save(update_fields=["brevo_id", "synced_at"])
            obj._syncing = False
            synced += 1

        self.message_user(request, f"Synced {synced} contact(s) to Brevo.")

    actions = ["sync_to_brevo", "pull_from_brevo"]

    @admin.action(description="Pull selected contacts from Brevo")
    def pull_from_brevo(
        self, request: HttpRequest, queryset: QuerySet[BrevoContact]
    ) -> None:
        """Refresh selected contacts from Brevo."""
        client = BrevoClient()
        updated = 0
        skipped = 0

        for obj in queryset:
            # Need either brevo_id or email to look up in Brevo
            identifier = obj.brevo_id or obj.email
            try:
                data = client.get_contact(identifier)
            except Exception:
                skipped += 1
                continue

            obj.brevo_id = data.get("id")
            obj.attributes = data.get("attributes", {})
            obj.synced_at = timezone.now()
            obj._syncing = True
            obj.save(update_fields=["brevo_id", "attributes", "synced_at"])
            obj._syncing = False
            updated += 1

        msg = f"Pulled {updated} contact(s) from Brevo."
        if skipped:
            msg += f" Skipped {skipped} (not found in Brevo)."
        self.message_user(request, msg)
