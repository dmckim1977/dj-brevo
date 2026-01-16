"""Django app configuration for dj-brevo"""

from django.apps import AppConfig


class DJBrevoConfig(AppConfig):
    """Configuration for dj-brevo Django app."""

    name = "dj_brevo"
    verbose_name = "Brevo Integration"

    def ready(self) -> None:
        """Run when Django has fully loaded this app.

        TODO Validate settings (API Key exists, etc)
        TODO Import signal handlers
        """

        pass
