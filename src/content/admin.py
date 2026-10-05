from django.contrib import admin

from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    BlogPage,
    CitiesPage,
    ContactsPage,
    CookiePage,
    FaqItem,
    FaqPage,
    HomePage,
    OfferPage,
    PrivacyPage,
    RatesPage,
    ReviewsPage,
    Service,
    ServicesPage,
)
from src.core.admin_mixins import ListUnfoldAdmin, SingletonUnfoldAdmin


def _register_page(model, content_fields, rich_fields=(), content_fieldsets=()):
    attrs = {
        'content_fields': content_fields,
        'content_fieldsets': content_fieldsets,
        'rich_fields': frozenset(rich_fields),
    }
    admin.site.register(
        model,
        type(f'{model.__name__}Admin', (SingletonUnfoldAdmin,), attrs),
    )


_register_page(
    HomePage,
    (),
    ('seo_block_body',),
    (
        ('Пошук і текст', {
            'fields': (
                'seo_title',
                'seo_description',
                'seo_block_title',
                'seo_block_body',
            ),
        }),
        ('Блок «Вигідний курс на USD та EUR»', {
            'fields': (
                'promo_image',
                'promo_kicker',
                'promo_title',
                'promo_title_accent',
                'promo_text',
                'promo_button',
            ),
        }),
    ),
)
_register_page(
    RatesPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    ServicesPage,
    (),
    ('intro',),
    (
        ('Пошук і текст', {
            'fields': ('title', 'intro', 'seo_title', 'seo_description'),
        }),
        ('Блок «Усі фінансові послуги в одному місці»', {
            'fields': (
                'hero_image',
                'hero_title',
                'hero_title_accent',
                'hero_text',
            ),
        }),
    ),
)
_register_page(
    AdvantagesPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    ContactsPage,
    ('title', 'intro', 'map_image', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    BlogPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    ReviewsPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    CitiesPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    FaqPage,
    ('title', 'intro', 'seo_title', 'seo_description'),
    ('intro',),
)
_register_page(
    PrivacyPage,
    ('title', 'body', 'seo_title', 'seo_description'),
    ('body',),
)
_register_page(
    OfferPage,
    ('title', 'body', 'seo_title', 'seo_description'),
    ('body',),
)
_register_page(
    CookiePage,
    ('title', 'body', 'seo_title', 'seo_description'),
    ('body',),
)


@admin.register(Service)
class ServiceAdmin(ListUnfoldAdmin):
    list_display = ('title', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('title',)}
    rich_fields = frozenset({'short_desc', 'body'})


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
    rich_fields = frozenset({'answer'})
