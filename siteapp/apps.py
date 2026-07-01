from django.apps import AppConfig


class SiteappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "siteapp"

    def ready(self):
        # Register fee-notification signal
        import siteapp.classroom_access  # noqa: F401
