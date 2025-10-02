"""Django settings for core project."""

from pathlib import Path

from django_tools.settings import DjangoSettings

# === Path Configuration ===
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = f"{BASE_DIR}/.env.produtos"

# === Settings Initialization ===
base_settings = DjangoSettings(env_file=ENV_FILE)

# === Security Settings ===
SECRET_KEY = base_settings.secret_key
DEBUG = base_settings.debug
print(f"ALLOWED_HOSTS: {base_settings.allowed_hosts}\nAPI_NAME: {base_settings.api_name}")
ALLOWED_HOSTS = base_settings.allowed_hosts

# === Application Definition ===
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "produto",
    "dj_cqrs",
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
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

# === Database ===
DATABASES = base_settings.databases

# === Authentication & Password Validation ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === Logging ===
LOGGING_CONFIG = "logging.config.dictConfig"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# === Celery Configuration ===
for key, value in base_settings.celery_config.items():
    celery_key = f"CELERY_{key.upper()}"
    globals()[celery_key] = value

# === Redis Configuration ===
for key, value in base_settings.redis_config.items():
    redis_key = f"REDIS_{key.upper()}"
    globals()[redis_key] = value

# === Cache Configuration ===
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": base_settings.redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "feed_cache",
        "TIMEOUT": 300,  # 5 minutos
    }
}

CQRS = {"transport": "dj_cqrs.transport.RabbitMQTransport", "url": base_settings.broker_url}


# === Internationalization ===
LANGUAGE_CODE = base_settings.language_code
TIME_ZONE = base_settings.time_zone
USE_I18N = base_settings.use_i18n
USE_TZ = base_settings.use_tz

# === Default Primary Key Field Type ===
DEFAULT_AUTO_FIELD = base_settings.default_auto_field

TEMPLATES = base_settings.templates

STATIC_URL = "static/"
