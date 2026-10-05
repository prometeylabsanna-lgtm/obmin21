import os

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core'
    label = 'core'
    verbose_name = 'Ядро'

    def ready(self):
        from django.conf import settings

        from src.core.admin_nav import build_unfold_navigation

        unfold = getattr(settings, 'UNFOLD', None)
        if isinstance(unfold, dict):
            sidebar = unfold.setdefault('SIDEBAR', {})
            sidebar['navigation'] = build_unfold_navigation()

        if os.environ.get('VERCEL'):
            from src.core.accent import ensure_vercel_accent
            from src.core.vercel_admin import ensure_vercel_admin

            ensure_vercel_admin()
            ensure_vercel_accent()
