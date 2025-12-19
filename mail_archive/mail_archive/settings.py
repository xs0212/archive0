"""Django settings for mail_archive project (production-grade).
Provides opinionated defaults for security, RBAC, MFA, audit logging,
object storage, and search integration.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "accounts",
    "archive",
    "audit",
    "searchapp",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "core.middleware.RequestIdMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ImmutableRequestMiddleware",
]

ROOT_URLCONF = "mail_archive.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "mail_archive.wsgi.application"
ASGI_APPLICATION = "mail_archive.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "mail_archive"),
        "USER": os.getenv("DB_USER", "mail_archive"),
        "PASSWORD": os.getenv("DB_PASSWORD", "mail_archive"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
            "init_command": "SET sql_notes=0",
        },
        "CONN_MAX_AGE": 60,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "TIMEOUT": 300,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Enterprise Mail Archive API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("APP_TIMEZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        }
    },
    "filters": {
        "request_id": {
            "()": "core.logging.RequestIdFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BEAT_SCHEDULE = {}

S3_STORAGE = {
    "ENDPOINT": os.getenv("S3_ENDPOINT", "http://127.0.0.1:9000"),
    "ACCESS_KEY": os.getenv("S3_ACCESS_KEY", "minio"),
    "SECRET_KEY": os.getenv("S3_SECRET_KEY", "minio123"),
    "BUCKET": os.getenv("S3_BUCKET", "mail-archive"),
    "REGION": os.getenv("S3_REGION", "us-east-1"),
    "LOCK_RETENTION_DAYS": int(os.getenv("S3_LOCK_DAYS", "365")),
}

ELASTICSEARCH = {
    "HOSTS": os.getenv("ES_HOSTS", "http://127.0.0.1:9200").split(","),
    "INDEX": os.getenv("ES_INDEX", "emails_archive"),
}

JWT_SETTINGS = {
    "ISSUER": os.getenv("JWT_ISSUER", "mail-archive"),
    "AUDIENCE": os.getenv("JWT_AUDIENCE", "mail-archive-clients"),
    "EXP_MINUTES": int(os.getenv("JWT_EXP_MINUTES", "30")),
    "SIGNING_KEY": os.getenv("JWT_SIGNING_KEY", "change-sign"),
    "VERIFYING_KEY": os.getenv("JWT_VERIFYING_KEY"),
}

MFA_SETTINGS = {
    "STEP_UP_ROLES": ["system_admin", "compliance_admin", "legal_user"],
    "REQUIRED_ACTIONS": {"EMAIL_SEARCH", "AUDIT_READ", "EXPORT_EMAIL"},
    "SESSION_TTL_MINUTES": int(os.getenv("MFA_SESSION_MINUTES", "480")),
}

AUDIT_SETTINGS = {
    "CHAIN_SALT": os.getenv("AUDIT_CHAIN_SALT", "audit-salt"),
}

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
