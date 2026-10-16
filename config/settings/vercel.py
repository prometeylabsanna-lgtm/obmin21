"""Test-only settings for Vercel Hobby (no dashboard env vars).

NOT for production. DigitalOcean remains the intended production target.
"""
import os
import shutil
from pathlib import Path

# Force values — Vercel may set empty strings; decouple then ignores defaults.
_TEST_ENV = {
    'SECRET_KEY': 'vercel-test-only-insecure-key-do-not-use-on-digitalocean',
    'ALLOWED_HOSTS': '.vercel.app,localhost,127.0.0.1',
    'RATE_HOLD_MINUTES': '30',
    'DEFAULT_FROM_EMAIL': 'noreply@obmin21.vercel.app',
    'TELEGRAM_BOT_TOKEN': '',
    'TELEGRAM_CHAT_ID': '',
    'TELEGRAM_WEBHOOK_SECRET': '',
    'PUBLIC_BASE_URL': '',
    'TELEGRAM_WEBHOOK_URL': '',
    'SECURE_SSL_REDIRECT': 'True',
    'DJANGO_LOG_LEVEL': 'INFO',
}
for _key, _value in _TEST_ENV.items():
    if not os.environ.get(_key):
        os.environ[_key] = _value

from .base import *  # noqa: E402, F403

DEBUG = True

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = ['.vercel.app', 'localhost', '127.0.0.1']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
]

def _ensure_crypto_flag(db_path):
    """Seed DB is copied as-is. Add the crypto switch if this deploy is ahead of it."""
    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'core_sitesettings' not in tables:
            return
        columns = {row[1] for row in connection.execute('PRAGMA table_info(core_sitesettings)')}
        if 'crypto_enabled' not in columns:
            connection.execute(
                'ALTER TABLE core_sitesettings ADD COLUMN crypto_enabled bool NOT NULL DEFAULT 1'
            )
        if 'django_migrations' in tables:
            exists = connection.execute(
                "SELECT 1 FROM django_migrations WHERE app='core' AND name='0006_sitesettings_crypto_enabled'"
            ).fetchone()
            if exists is None:
                connection.execute(
                    "INSERT INTO django_migrations (app, name, applied) "
                    "VALUES ('core', '0006_sitesettings_crypto_enabled', datetime('now'))"
                )
        connection.commit()
    finally:
        connection.close()


def _ensure_review_phone(db_path):
    """Seed DB is copied as-is. Add the review phone column if this deploy is ahead of it."""
    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'reviews_review' not in tables:
            return
        columns = {row[1] for row in connection.execute('PRAGMA table_info(reviews_review)')}
        if 'phone' not in columns:
            connection.execute(
                "ALTER TABLE reviews_review ADD COLUMN phone varchar(32) NOT NULL DEFAULT ''"
            )
        if 'django_migrations' in tables:
            exists = connection.execute(
                "SELECT 1 FROM django_migrations WHERE app='reviews' AND name='0004_review_phone'"
            ).fetchone()
            if exists is None:
                connection.execute(
                    "INSERT INTO django_migrations (app, name, applied) "
                    "VALUES ('reviews', '0004_review_phone', datetime('now'))"
                )
        connection.commit()
    finally:
        connection.close()


# Read-only deploy FS → copy seed DB to /tmp so admin/sessions can write.
_SEED_DB = BASE_DIR / 'db.sqlite3'  # noqa: F405
_RUNTIME_DB = Path('/tmp/obmin21.sqlite3')
if _SEED_DB.is_file() and not _RUNTIME_DB.exists():
    shutil.copy2(_SEED_DB, _RUNTIME_DB)
_ACTIVE_DB = _RUNTIME_DB if _RUNTIME_DB.exists() else _SEED_DB
if _ACTIVE_DB.is_file():
    _ensure_review_phone(_ACTIVE_DB)
    _ensure_crypto_flag(_ACTIVE_DB)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(_ACTIVE_DB),
    }
}

MEDIA_ROOT = Path('/tmp/obmin21-media')
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
