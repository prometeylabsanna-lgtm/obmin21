from django.contrib import admin

from src.bot.models import BotSession, TelegramProfile


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = (
        'chat_id',
        'username',
        'display_name',
        'phone',
        'city',
        'is_blocked',
        'updated_at',
    )
    list_filter = ('city', 'is_blocked')
    search_fields = ('chat_id', 'username', 'display_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'state', 'updated_at')
    search_fields = ('chat_id', 'state')
    readonly_fields = ('updated_at',)
