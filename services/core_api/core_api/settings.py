"""Django settings for Jingle core-api. All configuration comes from the environment (.env)."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

JINGLE_ENV = env("JINGLE_ENV", default="local")
JINGLE_DEMO = env.bool("JINGLE_DEMO", default=False)
DEBUG = env.bool("DJANGO_DEBUG", default=JINGLE_ENV == "local")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="test-only-secret-key")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://127.0.0.1:8080")
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS", default=[PUBLIC_BASE_URL, "http://127.0.0.1:8080"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "django_celery_beat",
    "core_api",
    "accounts",
    "sources",
    "feed",
]

MIDDLEWARE = [
    "core_api.middleware.RequestIdMiddleware",
    "core_api.middleware.UTCMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core_api.urls"
WSGI_APPLICATION = "core_api.wsgi.application"
ASGI_APPLICATION = "core_api.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///" + str(BASE_DIR / "test.sqlite3"))
}
DATABASES["default"]["CONN_MAX_AGE"] = 0  # PgBouncer-ready (Tech Bible 8.3)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

_REDIS_URL_ENV = env("REDIS_URL", default="")
REDIS_URL = _REDIS_URL_ENV or "redis://localhost:6379/0"
MONGO_URL = env("MONGO_URL", default="mongodb://localhost:27017/jingle")
QDRANT_URL = env("QDRANT_URL", default="http://localhost:6333")
INGEST_INTERNAL_URL = env("INGEST_INTERNAL_URL", default="http://localhost:8001")
SERVICE_TOKEN = env("SERVICE_TOKEN", default="test-service-token")

# Django cache: Redis when REDIS_URL is set (rate limits, idempotency, flags); locmem in tests.
if _REDIS_URL_ENV:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL_ENV,
            "KEY_PREFIX": "core",
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/api/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core_api.errors.exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Jingle API",
    "VERSION": "1.0.0",
    "OAS_VERSION": "3.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default="test-only-jwt-signing-key-000000000000"),
    "ISSUER": "jingle-core",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "typ",
}
REFRESH_COOKIE_NAME = "jingle_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_COOKIE_SECURE = JINGLE_ENV != "local"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = JINGLE_ENV != "local"
CSRF_COOKIE_SECURE = JINGLE_ENV != "local"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="memory://")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    # Backstop for JNG-01-10 / NFR-PRIV-03: purge soft-deleted accounts older than 30 days.
    "accounts-purge-due-users": {"task": "accounts.tasks.purge_due_users", "schedule": 6 * 3600},
}

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")

# Privacy (NFR-PRIV-01/02/03)
CONSENT_VERSION = env("CONSENT_VERSION", default="2026-09")
MINIMUM_AGE = 18
ACCOUNT_PURGE_AFTER_DAYS = 30
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Jingle <no-reply@jingle.local>")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "jingle_common.logging.JsonFormatter", "service": "core-api"}},
    "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["stdout"], "level": env("LOG_LEVEL", default="INFO")},
}


# ---- Refuse known or weak secrets outside local/test (S1-INGEST-security M6) ------------------
def _check_secrets() -> None:
    from django.core.exceptions import ImproperlyConfigured

    if JINGLE_ENV in {"local", "test"}:
        return
    weak = []
    for name, value in (
        ("DJANGO_SECRET_KEY", SECRET_KEY),
        ("JWT_SIGNING_KEY", SIMPLE_JWT["SIGNING_KEY"]),
        ("SERVICE_TOKEN", SERVICE_TOKEN),
    ):
        v = str(value or "")
        if len(v) < 32 or v.startswith(("test-", "dev-only-")) or v == "test-service-token":
            weak.append(name)
    if weak:
        raise ImproperlyConfigured(
            f"Set strong random values for {', '.join(weak)} when JINGLE_ENV={JINGLE_ENV!r}"
        )


_check_secrets()
