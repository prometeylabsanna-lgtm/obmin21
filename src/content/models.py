from django.db import models

from src.content.home_copy import HomeSectionCopy
from src.core.colors import ACCENT_DEFAULT, COLOR_HELP, hex_color_validator
from src.core.theme import bump_theme_cache


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        bump_theme_cache()

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ThemeFieldsMixin(models.Model):
    color_bg = models.CharField(
        'Колір фону',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    color_text = models.CharField(
        'Колір тексту',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    color_accent = models.CharField(
        'Колір підсвітки',
        max_length=7,
        default=ACCENT_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )

    class Meta:
        abstract = True


class HomePage(HomeSectionCopy, ThemeFieldsMixin, SingletonModel):
    theme_slug = 'home'
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)
    promo_image = models.ImageField(
        'Фото',
        upload_to='home/',
        blank=True,
        help_text='Блок «Вигідний курс на USD та EUR» на головній.',
    )
    promo_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='USD та EUR',
    )
    promo_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Вигідний курс',
    )
    promo_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='USD та EUR',
    )
    promo_text = models.CharField(
        'Текст',
        max_length=240,
        default='Обмінюйте валюту за актуальним курсом без зайвих кроків',
    )
    promo_button = models.CharField(
        'Текст кнопки',
        max_length=80,
        default='Обрати валюту',
    )
    seo_block_title = models.CharField(
        'Заголовок інформаційного блоку',
        max_length=160,
        default='Обмін валют',
    )
    seo_block_body = models.TextField('Текст інформаційного блоку', blank=True)

    class Meta:
        verbose_name = 'Головна сторінка'
        verbose_name_plural = 'Головна сторінка'

    def __str__(self):
        return 'Головна'


class HomeStat(models.Model):
    page = models.ForeignKey(
        HomePage,
        on_delete=models.CASCADE,
        related_name='stats',
        verbose_name='Головна',
    )
    number = models.CharField('Цифра', max_length=16)
    text = models.TextField('Текст картки')
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати', default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Картка «Чому нас обирають»'
        verbose_name_plural = 'Картки «Чому нас обирають»'

    def __str__(self):
        return self.number


class RatesPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'rates'
    title = models.CharField('Заголовок', max_length=120, default='Курси валют')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка курсів'
        verbose_name_plural = 'Сторінка курсів'

    def __str__(self):
        return self.title


class ServicesPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'services'
    title = models.CharField('Заголовок сторінки', max_length=120, default='Послуги')
    intro = models.TextField('Вступний текст', blank=True)
    hero_image = models.ImageField(
        'Фото',
        upload_to='services/',
        blank=True,
        help_text='Блок «Усі фінансові послуги в одному місці».',
    )
    hero_title = models.CharField(
        'Заголовок банера',
        max_length=120,
        default='Усі фінансові послуги',
    )
    hero_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='в одному місці',
    )
    hero_text = models.CharField(
        'Текст банера',
        max_length=320,
        default='Обмін валют, криптовалюти, перекази та інвестиційне золото з фіксацією курсу онлайн.',
    )
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка послуг'
        verbose_name_plural = 'Сторінка послуг'

    def __str__(self):
        return self.title


class Service(models.Model):
    title = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Адреса сторінки', unique=True, max_length=80)
    image = models.ImageField('Фото картки', upload_to='services/', blank=True)
    short_desc = models.TextField('Короткий опис')
    body = models.TextField('Повний опис', blank=True)
    show_on_home = models.BooleanField('Показувати на головній', default=True)
    home_page = models.ForeignKey(
        'HomePage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_cards',
        verbose_name='Головна',
    )
    is_active = models.BooleanField('Показувати на сайті', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Картка послуги'
        verbose_name_plural = 'Картки послуг'

    def __str__(self):
        return self.title


class AdvantagesPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'advantages'
    title = models.CharField('Заголовок', max_length=120, default='Переваги')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка переваг'
        verbose_name_plural = 'Сторінка переваг'

    def __str__(self):
        return self.title


class AdvantageItem(models.Model):
    class Audience(models.TextChoices):
        CITIZENS = 'citizens', 'Городянам'
        GUESTS = 'guests', 'Гостям міста'
        BUSINESS = 'business', 'Бізнесменам'

    audience = models.CharField('Для кого', max_length=16, choices=Audience.choices)
    text = models.CharField('Заголовок пункту', max_length=255)
    description = models.CharField('Короткий опис', max_length=320, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати на сайті', default=True)

    class Meta:
        ordering = ['audience', 'sort_order', 'id']
        verbose_name = 'Пункт переваги'
        verbose_name_plural = 'Пункти переваг'

    def __str__(self):
        return f'{self.get_audience_display()}: {self.text[:40]}'


class ContactsPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'contacts'
    title = models.CharField('Заголовок', max_length=120, default='Контакти')
    title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='з нами',
    )
    intro = models.TextField(
        'Вступний текст',
        blank=True,
        default=(
            'Відповімо на питання, підкажемо курс і допоможемо '
            'забронювати обмін у зручному відділенні.'
        ),
    )
    phone = models.CharField('Телефон', max_length=40, default='+38(044)444 44 44')
    phone_hint = models.CharField(
        'Підказка до телефону',
        max_length=80,
        default='Щодня з 8:00 до 21:00',
    )
    telegram = models.CharField('Telegram', max_length=80, default='@obmin21')
    telegram_hint = models.CharField(
        'Підказка до Telegram',
        max_length=80,
        default='Відповідаємо за кілька хвилин',
    )
    email = models.CharField('Email', max_length=80, default='info@obmin21.ua')
    email_hint = models.CharField(
        'Підказка до email',
        max_length=80,
        default='Для співпраці та бізнес-клієнтів',
    )
    hours = models.CharField(
        'Графік роботи',
        max_length=80,
        default='Пн–Нд, 8:00–21:00',
    )
    hours_hint = models.CharField(
        'Підказка до графіка',
        max_length=80,
        default='Без перерв і вихідних',
    )
    branches_kicker = models.CharField(
        'Підпис блоку відділень',
        max_length=80,
        default='Відділення',
    )
    branches_title = models.CharField(
        'Заголовок блоку відділень',
        max_length=120,
        default='Відділення',
    )
    branches_title_accent = models.CharField(
        'Акцент блоку відділень',
        max_length=80,
        default='по Україні',
    )
    map_image = models.ImageField('Зображення карти', upload_to='contacts/', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка контактів'
        verbose_name_plural = 'Сторінка контактів'

    def __str__(self):
        return self.title


class PrivacyPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'privacy'
    title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Політика конфіденційності',
    )
    body = models.TextField('Текст сторінки', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Політика конфіденційності'
        verbose_name_plural = 'Політика конфіденційності'

    def __str__(self):
        return self.title


class OfferPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'offer'
    title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Публічна оферта',
    )
    body = models.TextField('Текст сторінки', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Публічна оферта'
        verbose_name_plural = 'Публічна оферта'

    def __str__(self):
        return self.title


class CookiePage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'cookies'
    title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Політика використання файлів Cookie',
    )
    body = models.TextField('Текст сторінки', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Політика файлів cookie'
        verbose_name_plural = 'Політика файлів cookie'

    def __str__(self):
        return self.title


class CitiesPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'cities'
    title = models.CharField('Заголовок', max_length=120, default='Міста мережі')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка міст'
        verbose_name_plural = 'Сторінка міст'

    def __str__(self):
        return self.title


class FaqPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'faq'
    title = models.CharField('Заголовок', max_length=120, default='Часті питання')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка частих питань'
        verbose_name_plural = 'Сторінка частих питань'

    def __str__(self):
        return self.title


class FaqItem(models.Model):
    home_page = models.ForeignKey(
        HomePage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faq_items',
        verbose_name='Головна',
    )
    question = models.CharField('Питання', max_length=255)
    answer = models.TextField('Відповідь')
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати на сайті', default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Питання і відповідь'
        verbose_name_plural = 'Питання і відповіді'

    def __str__(self):
        return self.question[:60]


class BlogPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'blog'
    title = models.CharField('Заголовок', max_length=120, default='Блог')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка блогу'
        verbose_name_plural = 'Сторінка блогу'

    def __str__(self):
        return self.title


class ReviewsPage(ThemeFieldsMixin, SingletonModel):
    theme_slug = 'reviews'
    title = models.CharField('Заголовок', max_length=120, default='Відгуки')
    intro = models.TextField('Вступний текст', blank=True)
    seo_title = models.CharField('Заголовок у пошуку', max_length=160, blank=True)
    seo_description = models.CharField('Опис у пошуку', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка відгуків'
        verbose_name_plural = 'Сторінка відгуків'

    def __str__(self):
        return self.title


from src.content.cms_proxies import (  # noqa: E402,F401
    HomeArticlesSettings,
    HomeCalcSettings,
    HomeFaqSettings,
    HomePromoSettings,
    HomeReviewsSettings,
    HomeSearchSettings,
    HomeServicesSettings,
    HomeWhySettings,
)
