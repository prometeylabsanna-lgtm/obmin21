from dataclasses import replace

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from unfold.decorators import action

from src.core import admin_auth  # noqa: F401
from src.core.admin_mixins import SingletonUnfoldAdmin
from src.core.models import FooterSettings, HeaderSettings, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonUnfoldAdmin):
    actions_detail = ('toggle_crypto',)
    content_fields = (
        'site_name',
        'rate_hold_minutes',
        'telegram_url',
        'youtube_url',
        'instagram_url',
        'facebook_url',
        'notify_email',
        'notify_telegram_chat_id',
    )
    style_fields = ()

    def get_actions_detail(self, request, object_id):
        actions = super().get_actions_detail(request, object_id)
        enabled = SiteSettings.load().crypto_enabled
        label = 'Вимкнути Крипто' if enabled else 'Увімкнути Крипто'
        renamed = []
        for item in actions:
            if item.action_name.endswith('_toggle_crypto'):
                renamed.append(replace(item, description=label))
            else:
                renamed.append(item)
        return renamed

    @action(description='Вимкнути Крипто', url_path='toggle-crypto', icon='block')
    def toggle_crypto(self, request, object_id):
        settings = SiteSettings.load()
        settings.crypto_enabled = not settings.crypto_enabled
        settings.save(update_fields=['crypto_enabled'])
        if settings.crypto_enabled:
            messages.success(request, 'Крипто знову показується на сайті.')
        else:
            messages.success(
                request,
                'Крипто вимкнено: вкладка, валюти, статті, питання, послуги і нові записи з адмінки, де є згадка криптовалюти.',
            )
        return HttpResponseRedirect(
            reverse('admin:core_sitesettings_change', args=[settings.pk]),
        )


@admin.register(HeaderSettings)
class HeaderSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'header_logo',
    )
    style_fields = (
        'header_color_bg',
        'header_color_text',
        'header_color_accent',
        'header_color_highlight',
    )


@admin.register(FooterSettings)
class FooterSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'footer_logo',
        'footer_copy',
    )
    style_fields = (
        'footer_color_bg',
        'footer_color_text',
        'footer_color_accent',
        'footer_color_highlight',
    )
