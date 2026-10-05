from django.contrib import admin
from unfold.admin import StackedInline

from src.content.cms_proxies import (
    HomeArticlesSettings,
    HomeCalcSettings,
    HomeFaqSettings,
    HomePromoSettings,
    HomeReviewsSettings,
    HomeSearchSettings,
    HomeServicesSettings,
    HomeWhySettings,
)
from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    BlogPage,
    CitiesPage,
    ContactsPage,
    CookiePage,
    FaqItem,
    FaqPage,
    HomeStat,
    OfferPage,
    PrivacyPage,
    RatesPage,
    ReviewsPage,
    Service,
    ServicesPage,
)
from src.core.admin_mixins import ListUnfoldAdmin, SingletonUnfoldAdmin
from src.core.admin_widgets import CmsTinyMCE
from src.reviews.models import Review


class TinyStackedInline(StackedInline):
    rich_fields = frozenset()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.rich_fields:
            kwargs['widget'] = CmsTinyMCE()
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class HomeSectionAdmin(SingletonUnfoldAdmin):
    style_fields = ()


def _register_page(model, content_fields, rich_fields=(), content_fieldsets=(), admin_base=None):
    base = admin_base or SingletonUnfoldAdmin
    attrs = {
        'content_fields': content_fields,
        'content_fieldsets': content_fieldsets,
        'rich_fields': frozenset(rich_fields),
    }
    if base is HomeSectionAdmin:
        attrs['style_fields'] = ()
    admin.site.register(model, type(f'{model.__name__}Admin', (base,), attrs))


def _register_home(model, fields, rich_fields=(), inlines=(), extra=None):
    attrs = {
        'content_fields': fields,
        'rich_fields': frozenset(rich_fields),
        'style_fields': (),
        'inlines': list(inlines),
    }
    if extra:
        attrs.update(extra)
    admin.site.register(model, type(f'{model.__name__}Admin', (HomeSectionAdmin,), attrs))


class HomeStatInline(TinyStackedInline):
    model = HomeStat
    extra = 0
    fields = ('number', 'text', 'sort_order', 'is_active')
    rich_fields = frozenset({'text'})
    tab = True


class HomeFaqInline(TinyStackedInline):
    model = FaqItem
    extra = 0
    fields = ('question', 'answer', 'sort_order', 'is_active')
    fk_name = 'home_page'
    rich_fields = frozenset({'answer'})
    tab = True


class HomeReviewInline(TinyStackedInline):
    model = Review
    extra = 0
    fields = ('name', 'city_name', 'rating', 'text', 'is_published')
    fk_name = 'home_page'
    rich_fields = frozenset({'text'})
    tab = True


class HomeServiceInline(TinyStackedInline):
    model = Service
    extra = 0
    fields = ('title', 'image', 'short_desc', 'show_on_home', 'sort_order', 'is_active')
    fk_name = 'home_page'
    rich_fields = frozenset({'short_desc'})
    tab = True


_register_home(
    HomeCalcSettings,
    (
        'calc_kicker',
        'calc_title',
        'calc_title_accent',
        'calc_lead',
        'calc_give',
        'calc_get',
        'calc_rate_hint',
        'calc_button',
        'calc_lock',
        'calc_amount',
    ),
)
_register_home(
    HomePromoSettings,
    (
        'promo_image',
        'promo_kicker',
        'promo_title',
        'promo_title_accent',
        'promo_text',
        'promo_button',
    ),
)
_register_home(
    HomeWhySettings,
    ('why_kicker', 'why_title', 'why_title_accent'),
    ('text',),
    (HomeStatInline,),
)
_register_home(
    HomeServicesSettings,
    (
        'services_kicker',
        'services_title',
        'services_title_accent',
        'services_lead',
    ),
    ('short_desc',),
    (HomeServiceInline,),
)
_register_home(
    HomeFaqSettings,
    ('faq_kicker', 'faq_title', 'faq_title_accent'),
    ('answer',),
    (HomeFaqInline,),
)
_register_home(
    HomeReviewsSettings,
    ('reviews_kicker', 'reviews_title'),
    ('text',),
    (HomeReviewInline,),
)
_register_home(
    HomeArticlesSettings,
    (
        'articles_kicker',
        'articles_title',
        'articles_title_accent',
        'articles_lead',
        'featured_posts',
    ),
    extra={'filter_horizontal': ('featured_posts',)},
)
_register_page(
    HomeSearchSettings,
    ('seo_title', 'seo_description', 'seo_block_title', 'seo_block_body'),
    ('seo_block_body',),
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
        ('Банер сторінки', {
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
    (
        'title',
        'title_accent',
        'intro',
        'phone',
        'phone_hint',
        'telegram',
        'telegram_hint',
        'email',
        'email_hint',
        'hours',
        'hours_hint',
        'branches_kicker',
        'branches_title',
        'branches_title_accent',
        'map_image',
        'seo_title',
        'seo_description',
    ),
    ('intro',),
)
_register_page(BlogPage, ('title', 'intro', 'seo_title', 'seo_description'), ('intro',))
_register_page(ReviewsPage, ('title', 'intro', 'seo_title', 'seo_description'), ('intro',))
_register_page(CitiesPage, ('title', 'intro', 'seo_title', 'seo_description'), ('intro',))
_register_page(FaqPage, ('title', 'intro', 'seo_title', 'seo_description'), ('intro',))
_register_page(PrivacyPage, ('title', 'body', 'seo_title', 'seo_description'), ('body',))
_register_page(OfferPage, ('title', 'body', 'seo_title', 'seo_description'), ('body',))
_register_page(CookiePage, ('title', 'body', 'seo_title', 'seo_description'), ('body',))


@admin.register(Service)
class ServiceAdmin(ListUnfoldAdmin):
    list_display = ('title', 'slug', 'show_on_home', 'is_active', 'sort_order')
    list_editable = ('show_on_home', 'is_active', 'sort_order')
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
