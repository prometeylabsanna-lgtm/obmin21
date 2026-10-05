from django.contrib import admin

from src.bot.models import BotSession, ChatMessage, TelegramProfile
from src.core.admin_mixins import ListUnfoldAdmin


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ListUnfoldAdmin):
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
class BotSessionAdmin(ListUnfoldAdmin):
    list_display = ('chat_id', 'state', 'updated_at')
    search_fields = ('chat_id', 'state')
    readonly_fields = ('updated_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(ListUnfoldAdmin):
    list_display = ('id', 'chat_id', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('chat_id', 'text')
    readonly_fields = ('created_at',)
