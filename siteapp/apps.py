from django.apps import AppConfig


class SiteappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "siteapp"

    def ready(self):
        # Register fee-notification signal
        import siteapp.classroom_access  # noqa: F401
        # Register cache-invalidation signals
        from .signals import connect_signals
        connect_signals()

        # Optimize SQLite connections for high concurrency (WAL mode + 60s busy timeout)
        from django.db.backends.signals import connection_created
        def configure_sqlite_connection(sender, connection, **kwargs):
            if connection.vendor == "sqlite":
                cursor = connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA busy_timeout=60000;")
                cursor.execute("PRAGMA cache_size=-64000;")
                cursor.execute("PRAGMA mmap_size=268435456;")
        connection_created.connect(configure_sqlite_connection)
