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
        ('Обрати місто', {'fields': ('city_switch',)}),
        ('Банер', {
            'fields': (
                'banner_image',
                'banner_title',
                'banner_title_mode',
                'banner_suffix',
                'banner_suffix_mode',
                'banner_text',
                'banner_text_mode',
                'banner_button',
                'banner_button_mode',
            ),
        }),
    )


@admin.register(MapCity)
class MapCityAdmin(CitySectionAdmin):
    fieldsets = (
        ('Обрати місто', {'fields': ('city_switch',)}),
        ('Місто', {'fields': ('name', 'phone')}),
    )


@admin.register(ContactCity)
class ContactCityAdmin(CitySectionAdmin):
    inlines = [BranchInline]
    fieldsets = (
        ('Обрати місто', {'fields': ('city_switch',)}),
        ('Контакти міста', {'fields': ('name', 'phone')}),
    )


@admin.register(City)
class CityAdmin(ListUnfoldAdmin):
    list_display = ('name', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name',)
    fields = (
        'name',
        'phone',
        'is_active',
        'sort_order',
        'seo_title',
        'seo_title_mode',
        'seo_description',
        'seo_description_mode',
    )
    slug_source = 'name'


try:
    admin.site.unregister(Branch)
except admin.sites.NotRegistered:
    pass
