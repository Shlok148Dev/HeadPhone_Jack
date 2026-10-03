"""Django settings for Jingle core-api. All configuration comes from the environment (.env)."""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

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
    "social",
    "suggestions",
    "circles",
    "sends",
    "blends",
    "listening",
    "insights",
    "notifications",
    "rituals",
    "moderation",
    "artwork",
    "drops",
    "charts",
    "exports",
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
# 0 behind PgBouncer at scale (Tech Bible 8.3); the single-server pilot reuses connections.
# Persistent, health-checked connections: one per request cost ~5-10 ms (load test 2026-10).
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
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
        "OPTIONS": {"min_length": 10},
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
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "moderation.permissions.NotSuspended",
    ],
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
    "ENUM_NAME_OVERRIDES": {
        "SendKindEnum": "sends.models.Kind",
        "ModerationDecisionKindEnum": ["dismiss", "warn", "mute", "suspend", "ban"],
        "MusicPlatformEnum": "sources.connect_views.PLATFORMS",
        "CircleRoleEnum": "circles.models.Role",
    },
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
    # Jingle Connect: poll routes that can't push; resolve queued recordings (Tech Bible 2.3).
    "sources-poll": {"task": "sources.tasks.poll_sources", "schedule": 10.0},
    "sources-drain-identity": {"task": "sources.tasks.drain_identity_queue", "schedule": 60.0},
    # Friend suggestions nightly at 03:00 IST (Tech Bible 7.4); on-change runs are event-driven.
    # Sends: Played from the recipient's own listens; discovery credits daily (Tech Bible 6.4).
    # Rituals (Tech Bible 7.4): results within 5 min of close; recaps inside 48 h of month start.
    "battles-close": {"task": "rituals.tasks.close_due", "schedule": 60.0},
    "recaps-monthly": {
        "task": "rituals.tasks.make_recaps",
        "schedule": crontab(day_of_month="1,2", hour=6, minute=0),
    },
    "compat-recalibrate-monthly": {
        "task": "insights.tasks.recalibrate",
        "schedule": crontab(day_of_month=1, hour=5, minute=0),
    },
    "artwork-drain": {"task": "artwork.tasks.drain", "schedule": 60.0},
    # Demo only (no-op otherwise): personas post their Daily Drop over the day (JNG-14-01).
    "drops-demo": {"task": "drops.tasks.demo_drops", "schedule": 900.0},
    # Weekly charts: fold new listens into DailyPlays (D-CHART-03).
    "charts-refresh": {"task": "charts.tasks.refresh", "schedule": 3600.0},
    # Freeze last week (Monday 06:00 local) and announce it once (D-CHART-05).
    "charts-freeze": {"task": "charts.tasks.freeze", "schedule": 3600.0},
    "sessions-sweep": {"task": "listening.tasks.sweep", "schedule": 30.0},
    "sends-played": {"task": "sends.tasks.check_played", "schedule": 60.0},
    "sends-credits-daily": {
        "task": "sends.tasks.discovery_credits",
        "schedule": crontab(hour=4, minute=30),
    },
    "circles-suggest-weekly": {
        "task": "jingle_ml.tasks.suggest_circles",
        "schedule": crontab(hour=4, minute=0, day_of_week="sun"),
    },
    "suggestions-nightly": {
        "task": "jingle_ml.tasks.recompute_all",
        "schedule": crontab(hour=3, minute=0),
    },
}

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
# Play a circle playlist in order in your own app (D-EXPORT-01). Client ids are public (PKCE/GIS);
# YOUTUBE_API_KEY is used only server-side for song matching; Apple's key signs MusicKit tokens.
SPOTIFY_CLIENT_ID = env("SPOTIFY_CLIENT_ID", default="")
YOUTUBE_API_KEY = env("YOUTUBE_API_KEY", default="")
# Where "Add Jingle to Chrome" and "Get the Jingle app" point (D-CONNECT-01). Empty until published.
EXTENSION_STORE_URL = env("EXTENSION_STORE_URL", default="")
ANDROID_APP_URL = env("ANDROID_APP_URL", default="")
APPLE_MUSIC_TEAM_ID = env("APPLE_MUSIC_TEAM_ID", default="")
APPLE_MUSIC_KEY_ID = env("APPLE_MUSIC_KEY_ID", default="")
APPLE_MUSIC_PRIVATE_KEY_PATH = env("APPLE_MUSIC_PRIVATE_KEY_PATH", default="")
# Jingle account emails of the ≤ 5 direct-Spotify testers (ADR-0013).
SPOTIFY_ALLOWLIST = env("SPOTIFY_ALLOWLIST", default="")
# Sign-ups per IP (NFR-SEC-04). Keep 5/m in production; .env.example loosens it for local E2E.
AUTH_REGISTER_RATE = env("AUTH_REGISTER_RATE", default="5/m")
AUTH_LOGIN_RATE = env("AUTH_LOGIN_RATE", default="10/m")
# Failed sign-ins per account per hour before a temporary lockout (any IP). Not relaxed for dev.
# Apple catalogue fallback for song search (D-CAT-01); tests switch it off (no network).
# User uploads (profile photos). Served read-only by the edge at /media/ (never by Django).
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = "/media/"
AVATAR_MAX_BYTES = 5 * 1024 * 1024
CATALOGUE_SEARCH = env.bool("CATALOGUE_SEARCH", default=True)
API_DOCS_PUBLIC = env.bool("API_DOCS_PUBLIC", default=False)
AUTH_LOGIN_FAILURES_PER_HOUR = env.int("AUTH_LOGIN_FAILURES_PER_HOUR", default=20)
# Every page load refreshes; a pilot group behind one campus NAT shares an IP.
AUTH_REFRESH_RATE = env("AUTH_REFRESH_RATE", default="120/m")
# Web push (JNG-11-02): keys are generated locally; no keys means push is simply unavailable.
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = env("VAPID_SUBJECT", default="mailto:admin@jingle.local")

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
