from django.contrib import admin

from src.core.admin_city import (
    BranchInline,
    CityQuoteInline,
    CitySectionAdmin,
)
from src.core.admin_mixins import ListUnfoldAdmin
from src.network.cms_proxies import BannerCity, ContactCity, MapCity
from src.network.models import Branch, City


@admin.register(BannerCity)
class BannerCityAdmin(CitySectionAdmin):
    inlines = [CityQuoteInline]
    fieldsets = (
        (None, {'fields': ('city_switch',)}),
        ('Банер', {
            'fields': (
                'banner_image',
                'banner_title',
                'banner_suffix',
                'banner_text',
                'banner_button',
            ),
        }),
    )


@admin.register(MapCity)
class MapCityAdmin(CitySectionAdmin):
    inlines = [BranchInline]
    fieldsets = (
        (None, {'fields': ('city_switch',)}),
        ('Місто', {'fields': ('name', 'phone')}),
    )


@admin.register(ContactCity)
class ContactCityAdmin(CitySectionAdmin):
    inlines = [BranchInline]
    fieldsets = (
        (None, {'fields': ('city_switch',)}),
        ('Контакти міста', {'fields': ('name', 'phone')}),
    )


@admin.register(City)
class CityAdmin(ListUnfoldAdmin):
    list_display = ('name', 'slug', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [BranchInline]


@admin.register(Branch)
class BranchAdmin(ListUnfoldAdmin):
    list_display = ('address', 'city', 'phone', 'is_active', 'sort_order')
    list_filter = ('city', 'is_active')
    search_fields = ('address', 'phone')
