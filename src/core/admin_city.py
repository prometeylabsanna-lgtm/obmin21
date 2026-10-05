from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
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
    verbose_name = 'Відділення'
    verbose_name_plural = 'Відділення цього міста'


class CityQuoteInline(TabularInline):
    model = Quote
    extra = 0
    fields = ('pair', 'board', 'buy', 'sell', 'is_active')
    autocomplete_fields = ('pair',)
    verbose_name = 'Курс'
    verbose_name_plural = 'Курси на банері'
    tab = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(board__in=('retail', 'crypto'))


class CitySectionAdmin(ListUnfoldAdmin):
    list_display = ('name', 'slug', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('city_switch',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        city = City.objects.filter(is_active=True).order_by('sort_order', 'name').first()
        if city:
            return HttpResponseRedirect(
                reverse(
                    f'admin:{self.opts.app_label}_{self.opts.model_name}_change',
                    args=[city.pk],
                )
            )
        return super().changelist_view(request, extra_context)

    def city_switch(self, obj):
        if not obj or not obj.pk:
            return ''
        cities = City.objects.filter(is_active=True).order_by('sort_order', 'name')
        url_name = f'admin:{self.opts.app_label}_{self.opts.model_name}_change'
        parts = []
        for city in cities:
            url = reverse(url_name, args=[city.pk])
            css = ' is-current' if city.pk == obj.pk else ''
            parts.append((url, css, city.name))
        return format_html(
            '<div class="cms-city-switch"><span class="cms-city-switch__label">Місто</span>'
            '<div class="cms-city-switch__list">{}</div></div>',
            format_html_join(
                '',
                '<a class="cms-city-switch__btn{}" href="{}">{}</a>',
                ((css, url, name) for url, css, name in parts),
            ),
        )

    city_switch.short_description = 'Обрати місто'

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if object_id:
            city = City.objects.filter(pk=object_id).first()
            if city:
                ensure_city_quotes(city)
        return super().changeform_view(request, object_id, form_url, extra_context)
