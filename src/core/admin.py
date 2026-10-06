from src.core.admin_mixins import SingletonUnfoldAdmin
from src.core.models import FooterSettings, HeaderSettings, SiteSettings
from django.contrib import admin

from src.core import admin_auth  # noqa: F401


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'site_name',
        'default_phone',
        'rate_hold_minutes',
        'telegram_url',
        'youtube_url',
        'instagram_url',
        'facebook_url',
        'notify_email',
        'notify_telegram_chat_id',
    )
    style_fields = (
        'header_color_bg',
        'header_color_text',
        'header_color_accent',
        'footer_color_bg',
        'footer_color_text',
        'footer_color_accent',
    )


@admin.register(HeaderSettings)
class HeaderSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'site_name',
        'header_logo',
        'default_phone',
        'telegram_url',
    )
    style_fields = (
        'header_color_bg',
        'header_color_text',
        'header_color_accent',
    )


@admin.register(FooterSettings)
class FooterSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'footer_logo',
        'footer_copy',
        'telegram_url',
        'youtube_url',
        'instagram_url',
        'facebook_url',
        'default_phone',
    )
    style_fields = (
        'footer_color_bg',
        'footer_color_text',
        'footer_color_accent',
    )
