"""Minimal Django settings for testing"""

SECRET_KEY = "super-secret-key-not-for-production"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "dj_brevo",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

DJ_BREVO = {
    "API_KEY": "test-api-key",
    "DEFAULT_FROM_EMAIL": "test@example.com",
    "AUTO_SYNC": False,
}
