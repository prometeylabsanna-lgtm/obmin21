from django.contrib import admin

from src.core.admin_mixins import ListUnfoldAdmin
from src.rates.models import CurrencyPair, Quote


@admin.register(CurrencyPair)
class CurrencyPairAdmin(ListUnfoldAdmin):
    list_display = ('code', 'name', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('code',)}
    search_fields = ('code', 'name')


@admin.register(Quote)
class QuoteAdmin(ListUnfoldAdmin):
    list_display = ('pair', 'board', 'city', 'buy', 'sell', 'updated_at', 'is_active')
    list_filter = ('board', 'city', 'is_active')
    list_editable = ('buy', 'sell', 'is_active')
    search_fields = ('pair__code',)
