# rocky_herbals2/settings.py

from pathlib import Path
from celery.schedules import crontab

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production!
SECRET_KEY = "django-insecure-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ✅ Demo mode ON (safe for local testing)
DEBUG = False

# ✅ Allow local access
ALLOWED_HOSTS = [
    "rockysriherbals.com",
    "www.rockysriherbals.com",
    "app.rockysriherbals.com",
    "72.60.101.126",
    "127.0.0.1",
    "localhost",

    # ✅ Hostinger internal/probe domains (fix DisallowedHost)
    "srv1356217.hstgr.cloud",
    "autodiscover.srv1356217.hstgr.cloud",
    ".hstgr.cloud",  # allows any subdomain under hstgr.cloud
]
# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "billing",

    # ✅ Your app config (loads signals in apps.py)
    "herbalapp.apps.HerbalappConfig",

    # ✅ Celery results + beat
    "django_celery_results",
    "django_celery_beat",

    # ✅ Optional dev tools
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rocky_herbals2.urls"

# =========================
# ✅ Celery + Redis
# =========================
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_BACKEND = "django-db"

# =========================
# ✅ Cache (Redis) - IMPORTANT for throttling engine runs
# =========================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}

# =========================
# ✅ Celery timezone (IMPORTANT)
# =========================
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ENABLE_UTC = False

# (Optional but good)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 30  # 30 mins

# ==========================================================
# ✅ Celery Beat schedule (AUTO DAILY 11:59 PM)
# ==========================================================

CELERY_BEAT_SCHEDULE = {
    "mlm-engine-daily": {
        "task": "herbalapp.tasks.run_daily_engine_task",
        "schedule": crontab(hour=23, minute=59),
    }
}

# ✅ Correct template loading
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Global templates folder
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rocky_herbals2.wsgi.application"

# =========================
# ✅ PostgreSQL Database
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "rocky_herbals2",
        "USER": "rockyuser",
        "PASSWORD": "StrongPassword123",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ✅ Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ✅ TEMPORARY DEMO FIX — Disable login redirect
LOGIN_URL = "/"

# =========================
# ✅ SSL / NGINX SETTINGS
# =========================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False
CSRF_TRUSTED_ORIGINS = [
    "https://rockysriherbals.com",
    "https://www.rockysriherbals.com",
    "https://app.rockysriherbals.com",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# =========================
# ✅ Security headers (recommended)
# =========================
SECURE_HSTS_SECONDS = 86400  # 1 day (after confirm you can increase)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

