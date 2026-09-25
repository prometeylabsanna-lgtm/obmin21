import os

from django.core.wsgi import get_wsgi_application

# Vercel sets VERCEL=1. Force module — setdefault fails if key exists but empty.
if os.environ.get('VERCEL'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.vercel'
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
app = application
