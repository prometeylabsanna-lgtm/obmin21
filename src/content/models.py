from django.db import models

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


class HomePage(ThemeFieldsMixin, SingletonModel):
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
    short_desc = models.TextField('Короткий опис')
    body = models.TextField('Повний опис', blank=True)
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
    intro = models.TextField('Вступний текст', blank=True)
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
