# herbalapp/apps.py
from django.apps import AppConfig

class HerbalappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "herbalapp"

    def ready(self):
        # ✅ Only load signals
        from . import signals

