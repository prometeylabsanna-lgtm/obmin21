from django.contrib import admin

from src.core.models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': (
                'site_name',
                'logo_text',
                'logo_accent',
                'default_phone',
                'footer_copy',
                'rate_hold_minutes',
            ),
        }),
        ('Соцмережі', {
            'fields': ('telegram_url', 'youtube_url', 'instagram_url', 'facebook_url'),
        }),
        ('Сповіщення', {
            'fields': ('notify_email', 'notify_telegram_chat_id'),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
