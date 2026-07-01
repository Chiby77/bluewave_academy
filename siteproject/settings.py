"""
Django settings for Bluewave Academy.

Environment-aware: reads from .env locally, from Railway/host env vars in production.
"""

from pathlib import Path
import os
from django.contrib.messages import constants as messages

# ---------------------------------------------------------------------------
# BASE PATHS
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file when present (local dev / CI). Production injects vars directly.
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip(" \"'"))


# ---------------------------------------------------------------------------
# CORE
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-y4fyh1r6w2fa8ce&@e7cyry+1p&-6!dhq$0v=raz(#qo+8r&c_",
)

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "storages",          # django-storages (Supabase S3 backend)
    "siteapp",
]

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serve static files efficiently
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "siteproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
            ],
        },
    },
]

WSGI_APPLICATION = "siteproject.wsgi.application"
ASGI_APPLICATION = "siteproject.asgi.application"

# ---------------------------------------------------------------------------
# DATABASE — Railway PostgreSQL via DATABASE_URL (preferred) or explicit vars
# ---------------------------------------------------------------------------
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

if _DATABASE_URL:
    # Railway injects DATABASE_URL automatically when you add a Postgres plugin.
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=600,          # persistent connections — 10 min
            conn_health_checks=True,   # verify connection is alive before reuse
        )
    }
    # Force psycopg3 driver (psycopg[binary] installed)
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
elif os.environ.get("DATABASE_ENGINE", "sqlite3") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_NAME", "bluewave"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                # Keep idle connections alive on Railway
                "connect_timeout": 10,
                "options": "-c default_transaction_isolation=read\\ committed",
            },
        }
    }
else:
    # Local SQLite fallback
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 20,
                "check_same_thread": False,
            },
            "CONN_MAX_AGE": 60,
        }
    }

# ---------------------------------------------------------------------------
# CHANNELS — WebSocket layer
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "siteapp.CustomUser"

# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC FILES — WhiteNoise serves compressed, cached static assets
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# WhiteNoise: Brotli + gzip compression, long-lived cache headers for
# fingerprinted files, no-cache for non-fingerprinted ones.
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    # Media backend is set below — depends on whether Supabase is configured.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# ---------------------------------------------------------------------------
# MEDIA FILES — Supabase Storage (production) / local filesystem (dev)
# ---------------------------------------------------------------------------
SUPABASE_URL        = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY   = os.environ.get("SUPABASE_ANON_KEY", "")

# Supabase S3-compatible credentials
# Found in: Supabase Dashboard → Project Settings → Storage → S3 Connection
SUPABASE_S3_ENDPOINT   = os.environ.get("SUPABASE_S3_ENDPOINT", "")    # e.g. https://<ref>.supabase.co/storage/v1/s3
SUPABASE_S3_REGION     = os.environ.get("SUPABASE_S3_REGION", "auto")
SUPABASE_S3_ACCESS_KEY = os.environ.get("SUPABASE_S3_ACCESS_KEY", "")  # S3 Access Key ID
SUPABASE_S3_SECRET_KEY = os.environ.get("SUPABASE_S3_SECRET_KEY", "")  # S3 Secret Access Key

# Bucket names (create these in the Supabase dashboard)
SUPABASE_MEDIA_BUCKET  = os.environ.get("SUPABASE_MEDIA_BUCKET", "media")
SUPABASE_PAPERS_BUCKET = os.environ.get("SUPABASE_PAPERS_BUCKET", "papers")

_supabase_configured = all([
    SUPABASE_S3_ENDPOINT,
    SUPABASE_S3_ACCESS_KEY,
    SUPABASE_S3_SECRET_KEY,
])

if _supabase_configured:
    # All file uploads go to Supabase Storage via the S3-compatible API.
    STORAGES["default"] = {
        "BACKEND": "siteproject.storage_backends.SupabaseMediaStorage",
    }
    # MEDIA_URL points at the Supabase CDN/public base URL.
    # Files that need auth still go through signed URLs — this is only used
    # for public objects (blog images, thumbnails).
    MEDIA_URL = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_MEDIA_BUCKET}/"
    MEDIA_ROOT = ""  # not used in production — storage is remote
else:
    # Local development fallback
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ---------------------------------------------------------------------------
# FILE UPLOAD LIMITS
# Supports large PDFs (up to 50 MB) and video files (up to 500 MB).
# ---------------------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800      # 50 MB — files below this stay in RAM
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800      # 50 MB — matches above
FILE_UPLOAD_MAX_MEMORY_SIZE_VIDEO = 524288000   # informational; enforced in views
# Chunk large uploads to avoid blocking the event loop
FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

# ---------------------------------------------------------------------------
# CACHE — Redis (production) / LocMem (dev)
# ---------------------------------------------------------------------------
_REDIS_CACHE_URL = os.environ.get("REDIS_URL", "") or os.environ.get("CACHE_URL", "")

if _REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _REDIS_CACHE_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "IGNORE_EXCEPTIONS": True,    # degrade gracefully on Redis failure
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 20,
                },
            },
            "KEY_PREFIX": "bwa",
            "TIMEOUT": 300,
        }
    }
    # Store sessions in Redis for speed
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "bluewave-cache",
            "TIMEOUT": 300,
            "OPTIONS": {"MAX_ENTRIES": 5000},
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# ---------------------------------------------------------------------------
# SESSIONS
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 1209600        # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
LOGIN_URL = "siteapp:login"
LOGIN_REDIRECT_URL = "siteapp:dashboard"
LOGOUT_REDIRECT_URL = "siteapp:home"

# ---------------------------------------------------------------------------
# EMAIL
# ---------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = os.environ.get(
        "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
    )
    EMAIL_HOST     = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT     = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_USE_TLS  = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Bluewave Academy <noreply@bluewaveacademy.com>"
)

# ---------------------------------------------------------------------------
# MESSAGES
# ---------------------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG:   "debug",
    messages.INFO:    "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR:   "danger",
}

# ---------------------------------------------------------------------------
# PRODUCTION SECURITY HARDENING
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
    SESSION_COOKIE_SECURE  = True
    CSRF_COOKIE_SECURE     = True
    SECURE_BROWSER_XSS_FILTER    = True
    SECURE_CONTENT_TYPE_NOSNIFF  = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

    # HSTS — tells browsers to always use HTTPS for 1 year
    SECURE_HSTS_SECONDS            = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True

    # Proxy header trust (Railway sits behind a load balancer)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST    = True

# ---------------------------------------------------------------------------
# MISC
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging — structured for Railway's log drain
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "railway": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "railway",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "WARNING"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "siteapp": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "siteproject.storage_backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
