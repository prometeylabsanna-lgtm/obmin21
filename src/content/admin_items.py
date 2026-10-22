from django.contrib import admin
from django.utils.html import format_html

from src.content.admin import _register_page
from src.content.models import (
    AdvantageItem,
    BlogPage,
    CookiePage,
    FaqItem,
    HomeStat,
    OfferPage,
    PrivacyPage,
    Service,
)
from src.core.admin_mixins import ListUnfoldAdmin, SingletonUnfoldAdmin
from src.core.exchange_admin import ExchangeSafeAdminMixin, ExchangeSafeListFilter
from src.core.admin_widgets import CmsAdminTextareaWidget
from src.core.plain_text import html_to_plain_legal


class LegalBodyWidget(CmsAdminTextareaWidget):
    def format_value(self, value):
        return html_to_plain_legal(super().format_value(value) or '')


class LegalPageAdmin(SingletonUnfoldAdmin):
    rich_fields = frozenset()
    plain_fields = frozenset({'body'})

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'body':
            kwargs['widget'] = LegalBodyWidget(attrs={'rows': 20})
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


_register_page(
    PrivacyPage,
    ('title', 'body', 'seo_title', 'seo_description'),
    admin_base=LegalPageAdmin,
)
_register_page(
    OfferPage,
    ('title', 'body', 'seo_title', 'seo_description'),
    admin_base=LegalPageAdmin,
)
_register_page(
    CookiePage,
    ('title', 'body', 'seo_title', 'seo_description'),
    admin_base=LegalPageAdmin,
)


@admin.register(BlogPage)
class BlogPageAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'title',
        'title_mode',
        'heading',
        'title_accent',
        'intro',
        'intro_mode',
        'seo_title',
        'seo_title_mode',
        'seo_description',
        'seo_description_mode',
    )
    rich_fields = frozenset()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ('intro', 'intro_mode'):
            kwargs['widget'] = CmsAdminTextareaWidget()
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Service)
class ServiceAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = (
        'card_image',
        'title',
        'exchange_safe',
        'show_on_home',
        'is_active',
        'sort_order',
    )
    list_display_links = ('card_image', 'title')
    list_filter = (ExchangeSafeListFilter,)
    list_editable = ('show_on_home', 'is_active', 'sort_order')
    list_fullwidth = True
    rich_fields = frozenset({'body'})
    fields = (
        'exchange_safe',
        'image',
        'title',
        'short_desc',
        'short_desc_mode',
        'body',
        'block_text',
        'block_text_mode',
        'block_points',
        'block_points_mode',
        'block_cta',
        'block_cta_mode',
        'show_on_home',
        'is_active',
        'sort_order',
        'seo_title',
        'seo_description',
    )

    def card_image(self, obj):
        return format_html(
            '<img class="cms-svc-thumb" src="{}" alt="">',
            obj.image_src(),
        )

    card_image.short_description = 'Фото'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'short_desc':
            kwargs['widget'] = CmsAdminTextareaWidget(attrs={'rows': 4})
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(AdvantageItem)
class AdvantageItemAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = ('text', 'exchange_safe', 'audience', 'sort_order', 'is_active')
    list_filter = (ExchangeSafeListFilter, 'audience', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('text', 'description')
    fields = (
        'exchange_safe',
        'audience',
        'text',
        'description',
        'sort_order',
        'is_active',
    )


@admin.register(FaqItem)
class FaqItemAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = ('question', 'exchange_safe', 'sort_order', 'is_active')
    list_filter = (ExchangeSafeListFilter,)
    list_editable = ('sort_order', 'is_active')
    search_fields = ('question', 'answer')
    fields = ('exchange_safe', 'question', 'answer', 'sort_order', 'is_active')
    rich_fields = frozenset({'answer'})


@admin.register(HomeStat)
class HomeStatAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = ('number', 'exchange_safe', 'sort_order', 'is_active')
    list_filter = (ExchangeSafeListFilter, 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('number', 'text')
    fields = (
        'exchange_safe',
        'page',
        'number',
        'text',
        'sort_order',
        'is_active',
    )
