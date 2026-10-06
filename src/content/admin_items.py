from django.contrib import admin
from django.utils.html import format_html

from src.content.admin import _register_page
from src.content.models import (
    AdvantageItem,
    BlogPage,
    CookiePage,
    FaqItem,
    OfferPage,
    PrivacyPage,
    Service,
)
from src.core.admin_mixins import ListUnfoldAdmin, SingletonUnfoldAdmin
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
        'heading',
        'title_accent',
        'intro',
        'seo_title',
        'seo_description',
    )
    rich_fields = frozenset()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'intro':
            kwargs['widget'] = CmsAdminTextareaWidget()
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Service)
class ServiceAdmin(ListUnfoldAdmin):
    list_display = ('card_image', 'title', 'show_on_home', 'is_active', 'sort_order')
    list_display_links = ('card_image', 'title')
    list_editable = ('show_on_home', 'is_active', 'sort_order')
    list_fullwidth = True
    rich_fields = frozenset({'body'})
    fields = (
        'image',
        'title',
        'short_desc',
        'body',
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
class AdvantageItemAdmin(ListUnfoldAdmin):
    list_display = ('text', 'audience', 'sort_order', 'is_active')
    list_filter = ('audience', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('text', 'description')
    fields = ('audience', 'text', 'description', 'sort_order', 'is_active')


@admin.register(FaqItem)
class FaqItemAdmin(ListUnfoldAdmin):
    list_display = ('question', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('question', 'answer')
    fields = ('question', 'answer', 'sort_order', 'is_active')
    rich_fields = frozenset({'answer'})
