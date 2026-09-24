from django.core.cache import cache
from django.db import models


class SiteSettings(models.Model):
    site_name = models.CharField('Назва сайту', max_length=120, default='Обмін21')
    logo_text = models.CharField('Текст логотипу', max_length=40, default='ОБМІН')
    logo_accent = models.CharField('Акцент логотипу', max_length=10, default='21')
    telegram_url = models.URLField('Telegram', blank=True)
    youtube_url = models.URLField('YouTube', blank=True)
    instagram_url = models.URLField('Instagram', blank=True)
    facebook_url = models.URLField('Facebook', blank=True)
    rate_hold_minutes = models.PositiveIntegerField(
        'Хвилин фіксації курсу',
        default=30,
    )
    notify_email = models.EmailField('Email сповіщень', blank=True)
    notify_telegram_chat_id = models.CharField(
        'Telegram chat id',
        max_length=64,
        blank=True,
    )
    default_phone = models.CharField('Телефон за замовчуванням', max_length=32, blank=True)
    footer_copy = models.CharField(
        'Копірайт',
        max_length=120,
        default='© 2021–2026 Обмін21',
    )

    class Meta:
        verbose_name = 'Налаштування сайту'
        verbose_name_plural = 'Налаштування сайту'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('site_settings')

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
