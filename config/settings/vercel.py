"""Test-only settings for Vercel Hobby (no dashboard env vars).

NOT for production. DigitalOcean remains the intended production target.
"""
import os
import shutil
from pathlib import Path

# Defaults before base import — python-decouple has no .env on Vercel.
os.environ.setdefault(
    'SECRET_KEY',
    'vercel-test-only-insecure-key-do-not-use-on-digitalocean',
)
os.environ.setdefault('ALLOWED_HOSTS', '.vercel.app,localhost,127.0.0.1')
os.environ.setdefault('RATE_HOLD_MINUTES', '30')
os.environ.setdefault('DEFAULT_FROM_EMAIL', 'noreply@obmin21.vercel.app')
os.environ.setdefault('TELEGRAM_BOT_TOKEN', '')
os.environ.setdefault('TELEGRAM_CHAT_ID', '')
os.environ.setdefault('SECURE_SSL_REDIRECT', 'True')

from .base import *  # noqa: E402, F403

DEBUG = True

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = ['.vercel.app', 'localhost', '127.0.0.1']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
]

# Read-only deploy FS → copy seed DB to /tmp so admin/sessions can write.
_SEED_DB = BASE_DIR / 'db.sqlite3'  # noqa: F405
_RUNTIME_DB = Path('/tmp/obmin21.sqlite3')
if _SEED_DB.is_file() and not _RUNTIME_DB.exists():
    shutil.copy2(_SEED_DB, _RUNTIME_DB)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(_RUNTIME_DB if _RUNTIME_DB.exists() else _SEED_DB),
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

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
