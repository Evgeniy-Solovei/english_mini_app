import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

raw_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
ALLOWED_HOSTS = []
for h in raw_hosts:
    h = h.strip()
    if not h:
        continue
    if h.startswith("*."):
        h = "." + h[2:]
    ALLOWED_HOSTS.append(h)

if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "apps.users",
    "apps.learning",
    "apps.voice",
    "apps.bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

IS_TESTING = "test" in sys.argv or os.getenv("DJANGO_TESTING", "").lower() in ("1", "true", "yes")

# Production and local application runs use PostgreSQL exclusively. SQLite is
# intentionally limited to the disposable in-memory database used by tests.
if IS_TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("DJANGO_TEST_DATABASE_PATH", ":memory:"),
        }
    }
else:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ImproperlyConfigured("DATABASE_URL must use postgresql://; SQLite is not supported")
        query = parse_qs(parsed.query)
        db_options = {}
        if query.get("sslmode"):
            db_options["sslmode"] = query["sslmode"][0]
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": unquote(parsed.path.lstrip("/")),
                "USER": unquote(parsed.username or ""),
                "PASSWORD": unquote(parsed.password or ""),
                "HOST": parsed.hostname or "localhost",
                "PORT": parsed.port or 5432,
                "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
                "OPTIONS": db_options,
            }
        }
    else:
        db_password = os.getenv("DB_PASSWORD", "")
        if not db_password:
            raise ImproperlyConfigured("Set DB_PASSWORD or a PostgreSQL DATABASE_URL")
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DB_NAME", "english_bot"),
                "USER": os.getenv("DB_USER", "english_bot"),
                "PASSWORD": db_password,
                "HOST": os.getenv("DB_HOST", "localhost"),
                "PORT": int(os.getenv("DB_PORT", "5432")),
                "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Minsk")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
TELEGRAM_WEBAPP_URL = os.getenv("TELEGRAM_WEBAPP_URL", "http://localhost:8000/miniapp/")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]
TELEGRAM_INIT_DATA_MAX_AGE = int(os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", "86400"))

CORS_ALLOW_ALL_ORIGINS = DEBUG
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.trycloudflare.com",
    "https://web.telegram.org",
    "https://english-bot.live-dev.by",
]
for host in ALLOWED_HOSTS:
    if host.startswith("http"):
        CSRF_TRUSTED_ORIGINS.append(host)
    elif host != "*" and not host.startswith("."):
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "yes")


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "")

# Voice cache
VOICE_CACHE_DIR = MEDIA_ROOT / "voice_cache"
