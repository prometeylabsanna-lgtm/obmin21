from django.contrib import admin

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
    AdvantagesPage,
    CitiesPage,
    ContactsPage,
    FaqPage,
    RatesPage,
    ReviewsPage,
    ServicesPage,
)
from src.core.admin_mixins import SingletonUnfoldAdmin
from src.core.admin_widgets import CmsAdminTextareaWidget


class HomeSectionAdmin(SingletonUnfoldAdmin):
    style_fields = ()


def _register_page(model, content_fields, rich_fields=(), content_fieldsets=(), admin_base=None, extra=None):
    base = admin_base or SingletonUnfoldAdmin
    attrs = {
        'content_fields': content_fields,
        'content_fieldsets': content_fieldsets,
        'rich_fields': frozenset(rich_fields),
    }
    if extra:
        attrs.update(extra)
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
    (
        'show_why',
        'why_kicker',
        'why_title',
        'why_title_accent',
    ),
    extra={
        'content_fieldsets': ((
            'Контент',
            {
                'description': (
                    'Лише заголовок блоку на головній. '
                    'Цифри — зі сторінки Переваги.'
                ),
                'fields': (
                    'show_why',
                    'why_kicker',
                    'why_title',
                    'why_title_accent',
                ),
            },
        ),),
    },
)
_register_home(
    HomeServicesSettings,
    (
        'show_services',
        'services_kicker',
        'services_title',
        'services_title_accent',
        'services_lead',
    ),
    extra={
        'content_fieldsets': ((
            'Контент',
            {
                'description': (
                    'Картки послуг додавайте в розділі Послуги. '
                    'Тут лише заголовок блоку на головній.'
                ),
                'fields': (
                    'show_services',
                    'services_kicker',
                    'services_title',
                    'services_title_accent',
                    'services_lead',
                ),
            },
        ),),
    },
)
_register_home(
    HomeFaqSettings,
    (
        'show_faq',
        'faq_kicker',
        'faq_title',
        'faq_title_accent',
    ),
    extra={
        'content_fieldsets': ((
            'Контент',
            {
                'description': (
                    'Питання редагуйте в розділі Питання і відповіді. '
                    'Тут лише заголовок блоку на головній.'
                ),
                'fields': (
                    'show_faq',
                    'faq_kicker',
                    'faq_title',
                    'faq_title_accent',
                ),
            },
        ),),
    },
)
_register_home(
    HomeReviewsSettings,
    (
        'show_reviews',
        'reviews_kicker',
        'reviews_title',
    ),
    extra={
        'content_fieldsets': ((
            'Контент',
            {
                'description': (
                    'Відгуки редагуйте в розділі Відгуки. '
                    'Тут лише заголовок блоку на головній.'
                ),
                'fields': (
                    'show_reviews',
                    'reviews_kicker',
                    'reviews_title',
                ),
            },
        ),),
    },
)


class HomeArticlesAdmin(HomeSectionAdmin):
    content_fields = (
        'show_articles',
        'articles_kicker',
        'articles_title',
        'articles_title_accent',
        'articles_lead',
    )
    content_fieldsets = (
        ('Контент', {
            'description': (
                'Статті беруться з розділу Блог. '
                'Тут лише заголовок блоку на головній.'
            ),
            'fields': (
                'show_articles',
                'articles_kicker',
                'articles_title',
                'articles_title_accent',
                'articles_lead',
            ),
        }),
    )
    style_fields = ()


admin.site.register(HomeArticlesSettings, HomeArticlesAdmin)


class HomeLookAdmin(HomeSectionAdmin):
    content_fieldsets = (
        ('Оформлення', {
            'fields': (
                'color_bg',
                'color_text',
                'color_accent',
                'color_highlight',
            ),
        }),
    )
    style_fields = ()


admin.site.register(HomeSearchSettings, HomeLookAdmin)


class RatesPageAdmin(SingletonUnfoldAdmin):
    content_fieldsets = (
        ('Контент', {
            'description': (
                'Це сторінка сайту /kursy/ — «Всі валюти». '
                'Тут лише заголовки й текст над таблицею. '
                'Валютні пари та таблиця курсів — пункти нижче в цьому розділі.'
            ),
            'fields': ('title', 'intro', 'seo_title', 'seo_description'),
        }),
    )
    rich_fields = frozenset()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'intro':
            kwargs['widget'] = CmsAdminTextareaWidget(attrs={'rows': 4})
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


admin.site.register(RatesPage, RatesPageAdmin)


class AdvantagesPageAdmin(SingletonUnfoldAdmin):
    rich_fields = frozenset({'cmp_us_html', 'cmp_them_html'})
    content_fieldsets = (
        ('Чому обирають Обмін21', {
            'fields': (
                'title',
                'seo_title',
                'seo_description',
                'hero_kicker',
                'hero_title',
                'hero_title_accent',
                'hero_lead',
                'hero_btn_primary',
                'hero_btn_secondary',
                'hero_banner',
                'color_hero_bg',
                'hero_cards_image',
            ),
        }),
        ('Обмін21 у цифрах', {
            'fields': (
                'stats_kicker',
                'stats_title',
                'stats_title_accent',
                'stat_1_title',
                'stat_1_text',
                'stat_2_title',
                'stat_2_text',
                'stat_3_title',
                'stat_3_text',
                'stat_4_title',
                'stat_4_text',
            ),
        }),
        ('Чому люди обирають обмінювати в Обмін21', {
            'fields': (
                'why_kicker',
                'why_title',
                'why_title_accent',
                'why_lead',
                'why_banner',
                'color_why_banner',
                'why_coins',
                'why_banner_title',
                'why_banner_accent',
                'why_banner_text',
                'why_1_title',
                'why_1_text',
                'why_2_title',
                'why_2_text',
                'why_3_title',
                'why_3_text',
                'why_4_title',
                'why_4_text',
                'why_5_title',
                'why_5_text',
            ),
        }),
        ('Обмін21 чи звичайний обмінник', {
            'fields': (
                'cmp_kicker',
                'cmp_title',
                'cmp_title_accent',
                'cmp_us_html',
                'cmp_them_html',
                'cmp_btn',
            ),
        }),
    )


admin.site.register(AdvantagesPage, AdvantagesPageAdmin)
_register_page(
    ServicesPage,
    (),
    (),
    (
        ('Пошук', {
            'fields': ('title', 'seo_title', 'seo_description'),
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
    ContactsPage,
    (
        'title',
        'heading',
        'title_accent',
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
        'seo_title',
        'seo_description',
    ),
)
_register_page(CitiesPage, ('title', 'intro', 'seo_title', 'seo_description'))
_register_page(
    FaqPage,
    (
        'kicker',
        'title',
        'title_accent',
        'lead',
        'cta_title',
        'cta_title_accent',
        'cta_text',
        'cta_phone',
        'cta_telegram',
        'seo_title',
        'seo_description',
    ),
    extra={
        'content_fieldsets': (
            ('Заголовок сторінки', {
                'description': (
                    'Питання додавайте в пункті «Питання» цього розділу. '
                    'Той самий список показується на головній та інших сторінках.'
                ),
                'fields': (
                    'kicker',
                    'title',
                    'title_accent',
                    'lead',
                    'seo_title',
                    'seo_description',
                ),
            }),
            ('Підказка внизу', {
                'fields': (
                    'cta_title',
                    'cta_title_accent',
                    'cta_text',
                    'cta_phone',
                    'cta_telegram',
                ),
            }),
        ),
    },
)
_register_page(
    ReviewsPage,
    (
        'kicker',
        'title',
        'title_accent',
        'cta_button',
        'seo_title',
        'seo_description',
    ),
    extra={
        'content_fieldsets': (
            ('Заголовок сторінки', {
                'description': (
                    'Відгуки додавайте в пункті «Відгуки клієнтів». '
                    'Той самий список показується на головній, послугах, перевагах і FAQ.'
                ),
                'fields': (
                    'kicker',
                    'title',
                    'title_accent',
                    'cta_button',
                    'seo_title',
                    'seo_description',
                ),
            }),
        ),
    },
)


from src.content import admin_items  # noqa: F401,E402
