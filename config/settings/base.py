"""
Base settings shared by all environments. Values come from the environment
(.env in dev) so the same code runs locally or against cloud Postgres/Redis.
"""
from pathlib import Path

import environ

# Project root: config/settings/base.py -> parents[2]
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
)
# Load .env if present (optional — real envs set vars directly).
environ.Env.read_env(BASE_DIR / ".env")

# --- Core ---
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me-not-for-production-0123456789")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_q",
    "corsheaders",
    # Local apps
    "apps.tenants",
    "apps.flows",
    "apps.conversations",
    "apps.channels",
    "apps.handoff",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database (D1-04) ---
# Set DATABASE_URL to your cloud Postgres (e.g. Neon). Falls back to local
# SQLite so the project boots before the cloud DB is configured.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# --- Async queue: django-q2 (DB-backed broker — no Redis) — D-108 ---
Q_CLUSTER = {
    "name": "chatbot_platform",
    "orm": "default",          # use the Django database as the broker
    "workers": 2,
    "timeout": 60,
    "retry": 120,              # must exceed timeout
    "max_attempts": 3,         # ERR-02: retry up to 3 times
    "catch_up": False,
    "save_limit": 250,
}

# --- DRF + JWT auth (D1-11) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # Pagination: list endpoints return {count,next,previous,results}, 50/page,
    # client may request up to 200 via ?page_size= (config.pagination caps it).
    # Prevents unbounded conversation-log/audit responses as tenants grow.
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    # Throttling: protect the API and (via the "login" scope) the JWT endpoint
    # from brute force. The webhook is deliberately NOT throttled — see config/urls.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",   # authenticated product owner — generous
        "anon": "20/hour",     # unauthenticated surface is tiny
        "login": "5/min",      # JWT token endpoint — brute-force guard
    },
}

# --- Credential encryption (D1-06 / SEC-02 / D-100 = Fernet) ---
# Key from env; never stored in the DB (D-106). dev.py sets a dev-only default.
FERNET_KEY = env("FERNET_KEY", default="")

# --- Email: handoff notifications (D1-24 / D-108) ---
# Console backend by default (prints); prod sets a real backend (Resend/SMTP) via env.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Relay <noreply@relay.local>")

# --- CORS: allow the separate React SPA origin (D-109) ---
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://localhost:3000"],
)

# --- Meta Cloud API (D-101): webhook security ---
META_APP_SECRET = env("META_APP_SECRET", default="")              # HMAC of webhook (SEC-01)
META_WEBHOOK_VERIFY_TOKEN = env("META_WEBHOOK_VERIFY_TOKEN", default="")  # GET verify (WA-04)
META_GRAPH_VERSION = env("META_GRAPH_VERSION", default="v21.0")

# --- Auth password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18n / TZ ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Logging & monitoring ---
# Logs go to stdout; Railway captures stdout as the app log stream (no file
# handlers — the host filesystem is ephemeral). Our code logs only tenant IDs
# and HTTP status, never tokens or customer content (SEC-02 / SEC-04).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
        },
    },
    # Root catches everything at WARNING; our app loggers (apps.*) at INFO.
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# --- Static ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
