from django.contrib import admin
from unfold.admin import TabularInline

from src.core.admin_mixins import ListUnfoldAdmin
from src.network.models import Branch, City
from src.rates.models import Quote
from src.rates.services import ensure_city_quotes


class BranchInline(TabularInline):
    model = Branch
    extra = 0
    fields = ('address', 'hours', 'phone', 'is_active', 'sort_order')
    tab = True


class CityQuoteInline(TabularInline):
    model = Quote
    extra = 0
    fields = ('pair', 'board', 'buy', 'sell', 'is_active')
    autocomplete_fields = ('pair',)
    verbose_name = 'Курс'
    verbose_name_plural = 'Курси в калькуляторі для цього міста'
    tab = True


@admin.register(City)
class CityAdmin(ListUnfoldAdmin):
    list_display = ('name', 'slug', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [CityQuoteInline, BranchInline]
    fieldsets = (
        ('Місто', {
            'fields': ('name', 'slug', 'phone', 'is_active', 'sort_order'),
        }),
        ('Банер на головній', {
            'fields': (
                'banner_image',
                'banner_title',
                'banner_suffix',
                'banner_text',
            ),
            'description': 'Фото, заголовок і підпис змінюються разом із вибраним містом.',
        }),
        ('Пошук', {
            'fields': ('seo_title', 'seo_description'),
        }),
    )

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if object_id:
            city = City.objects.filter(pk=object_id).first()
            if city:
                ensure_city_quotes(city)
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(Branch)
class BranchAdmin(ListUnfoldAdmin):
    list_display = ('address', 'city', 'phone', 'is_active', 'sort_order')
    list_filter = ('city', 'is_active')
    search_fields = ('address', 'phone')
