"""Vercel serverless WSGI entry for Django (test deploy)."""
import os
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.vercel')
os.environ.setdefault(
    'SECRET_KEY',
    'vercel-test-only-insecure-key-do-not-use-on-digitalocean',
)

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()

# WhiteNoise needs STATIC_ROOT; Hobby build may skip custom installCommand.
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

_static_root = Path(settings.STATIC_ROOT)
if not _static_root.is_dir() or not any(_static_root.iterdir()):
    call_command('collectstatic', interactive=False, verbosity=0)

app = application
