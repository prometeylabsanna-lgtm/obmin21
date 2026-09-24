from django.contrib import admin

from src.leads.models import ContactMessage, ExchangeRequest


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'phone',
        'pair',
        'direction',
        'city',
        'status',
        'expires_at',
        'created_at',
    )
    list_filter = ('status', 'city', 'direction')
    search_fields = ('name', 'phone')
    readonly_fields = ('created_at', 'expires_at', 'rate_fixed')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'city', 'is_processed', 'created_at')
    list_filter = ('is_processed', 'city')
    search_fields = ('name', 'phone', 'message')
