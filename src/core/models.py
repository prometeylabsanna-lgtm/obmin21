from django.core.cache import cache
from django.db import models

from src.core.colors import (
    ACCENT_DEFAULT,
    ACCENT_HOVER_DEFAULT,
    COLOR_HELP,
    hex_color_validator,
)
from src.core.theme import bump_theme_cache


class SiteSettings(models.Model):
    site_name = models.CharField('Назва сайту', max_length=120, default='Обмін21')
    logo_text = models.CharField('Текст логотипу', max_length=40, default='ОБМІН')
    logo_accent = models.CharField('Акцент логотипу', max_length=10, default='21')
    header_logo = models.ImageField(
        'Логотип у шапці',
        upload_to='chrome/',
        blank=True,
        help_text='Якщо порожньо — лишається стандартний логотип.',
    )
    footer_logo = models.ImageField(
        'Логотип у підвалі',
        upload_to='chrome/',
        blank=True,
        help_text='Якщо порожньо — лишається стандартний логотип.',
    )
    telegram_url = models.URLField('Посилання Telegram', blank=True)
    youtube_url = models.URLField('Посилання YouTube', blank=True)
    instagram_url = models.URLField('Посилання Instagram', blank=True)
    facebook_url = models.URLField('Посилання Facebook', blank=True)
    rate_hold_minutes = models.PositiveIntegerField(
        'Хвилин фіксації курсу',
        default=30,
    )
    notify_email = models.EmailField('Email для сповіщень', blank=True)
    notify_telegram_chat_id = models.CharField(
        'Номер чату Telegram для сповіщень',
        max_length=64,
        blank=True,
    )
    default_phone = models.CharField('Телефон, якщо місто не обрано', max_length=32, blank=True)
    footer_copy = models.CharField(
        'Рядок копірайту внизу',
        max_length=120,
        default='© 2026. Обмін21. Усі права захищені',
    )
    header_color_bg = models.CharField(
        'Колір фону шапки',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_text = models.CharField(
        'Колір тексту шапки',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_accent = models.CharField(
        'Колір акценту шапки',
        max_length=7,
        default=ACCENT_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_highlight = models.CharField(
        'Колір підсвітки шапки',
        max_length=7,
        default=ACCENT_HOVER_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_bg = models.CharField(
        'Колір фону підвалу',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_text = models.CharField(
        'Колір тексту підвалу',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_accent = models.CharField(
        'Колір акценту підвалу',
        max_length=7,
        default=ACCENT_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_highlight = models.CharField(
        'Колір підсвітки підвалу',
        max_length=7,
        default=ACCENT_HOVER_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )

    class Meta:
        verbose_name = 'Загальні налаштування'
        verbose_name_plural = 'Загальні налаштування'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('site_settings')
        bump_theme_cache()

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        cached = cache.get('site_settings')
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set('site_settings', obj, 300)
        return obj


class HeaderSettings(SiteSettings):
    class Meta:
        proxy = True
        verbose_name = 'Шапка сайту'
        verbose_name_plural = 'Шапка сайту'


class FooterSettings(SiteSettings):
    class Meta:
        proxy = True
        verbose_name = 'Підвал сайту'
        verbose_name_plural = 'Підвал сайту'
