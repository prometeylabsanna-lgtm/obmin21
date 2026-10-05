from django.contrib import admin

from src.core.admin_mixins import ListUnfoldAdmin
from src.leads.models import ContactMessage, ExchangeRequest


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(ListUnfoldAdmin):
    list_display = (
        'id',
        'name',
        'phone',
        'pair',
        'direction',
        'city',
        'status',
        'source',
        'created_at',
    )
    list_filter = ('status', 'city', 'direction', 'source')
    search_fields = ('name', 'phone')
    readonly_fields = ('created_at', 'expires_at', 'rate_fixed')


@admin.register(ContactMessage)
class ContactMessageAdmin(ListUnfoldAdmin):
    list_display = ('id', 'name', 'phone', 'city', 'source', 'is_processed', 'created_at')
    list_filter = ('is_processed', 'city', 'source')
    search_fields = ('name', 'phone', 'message')
