# herbalapp/apps.py

from django.apps import AppConfig


class HerbalappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "herbalapp"

    def ready(self):
        """
        Auto-load signals on app startup.
        Ensures `post_save` for Member triggers date-driven MLM engine.
        """

