"""Settings for dj-brevo.

Access django settings via the `brevo_settings`

    from dj_brevo.settings import brevo_settings
    api_key = brevo_settings.API_KEY

User configuration is read from Django settings:

    # settings.py
    DJ_BREVO = {
        "API_KEY": "api_key_xxx",
    }
"""

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

DEFAULTS: dict[str, Any] = {
    "API_KEY": None,
    "DEFAULT_FROM_EMAIL": None,
    "TIMEOUT": 10,
    "API_BASE_URL": "https://api.brevo.com/v3",
    "SANDBOX": False,
    "AUTO_SYNC": True,
}


@dataclass
class BrevoSettings:
    """Type-safe access to DJ_BREVO settings."""

    _user_settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._user_settings = getattr(settings, "DJ_BREVO", {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        if name not in DEFAULTS:
            raise AttributeError(f"Invalid setting: {name!r}")

        # user setting takes priority, otherwise use default
        if name in self._user_settings:
            return self._user_settings[name]
        return DEFAULTS[name]


brevo_settings = BrevoSettings()
