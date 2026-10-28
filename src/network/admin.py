from django.contrib import admin, messages
from unfold.admin import TabularInline

from src.core.admin_city import (
    BranchInline,
    CityQuoteInline,
    CitySectionAdmin,
)
from src.core.admin_mixins import ListUnfoldAdmin, _strip_plain_fields
from src.network.cms_proxies import BannerCity, ContactCity, MapCity
from src.network.geocoding import (
    GEOCODE_FAILURE,
    GEOCODE_SUCCESS,
    apply_admin_coordinates,
    geocode_action_summary,
    geocode_queryset,
)
from src.network.hours import sync_branch_hours_text
from src.network.models import Branch, BranchOpeningHours, City


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
        ('Місто', {'fields': ('name', 'name_mode', 'phone')}),
    )


@admin.register(ContactCity)
class ContactCityAdmin(CitySectionAdmin):
    inlines = [BranchInline]
    fieldsets = (
        ('Обрати місто', {'fields': ('city_switch',)}),
        ('Контакти міста', {'fields': ('name', 'name_mode', 'phone')}),
    )


class BranchOpeningHoursInline(TabularInline):
    model = BranchOpeningHours
    extra = 0
    fields = ('day_of_week', 'opens', 'closes', 'is_closed')
    ordering = ('day_of_week',)
    verbose_name = 'День'
    verbose_name_plural = 'Графік по днях'


@admin.register(Branch)
class BranchAdmin(ListUnfoldAdmin):
    list_display = ('city', 'address', 'is_active', 'sort_order')
    list_filter = ('city', 'is_active')
    search_fields = ('address', 'city__name')
    inlines = [BranchOpeningHoursInline]
    actions = ('geocode_coordinates', 'delete_selected')
    readonly_fields = ('hours', 'coords_manual')
    fields = (
        'city',
        'address',
        'hours',
        'phone',
        'map_embed_url',
        'map_url',
        'lat',
        'lng',
        'coords_manual',
        'is_active',
        'sort_order',
    )

    def save_model(self, request, obj, form, change):
        _strip_plain_fields(obj, self.rich_fields)
        apply_admin_coordinates(request, obj, form)
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sync_branch_hours_text(form.instance)

    @admin.action(description='Визначити координати')
    def geocode_coordinates(self, request, queryset):
        counts = geocode_queryset(queryset.select_related('city'))
        messages.info(request, geocode_action_summary(**counts))
        if counts['found']:
            messages.info(request, GEOCODE_SUCCESS)
        if counts['missing']:
            messages.warning(request, GEOCODE_FAILURE)


@admin.register(City)
class CityAdmin(ListUnfoldAdmin):
    list_display = ('name', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name',)
    fields = (
        'name',
        'name_mode',
        'phone',
        'is_active',
        'sort_order',
        'seo_title',
        'seo_title_mode',
        'seo_description',
        'seo_description_mode',
    )
    slug_source = 'name'
