from django.db import models
from django.utils import timezone

from src.network.models import City


class RateBoard(models.TextChoices):
    RETAIL = 'retail', 'Роздріб'
    WHOLESALE = 'wholesale', 'Опт'
    CROSS = 'cross', 'Крос'
    CRYPTO = 'crypto', 'Крипто'


class CurrencyPair(models.Model):
    code = models.CharField('Код', max_length=16)
    name = models.CharField('Назва', max_length=80)
    slug = models.SlugField('Slug', unique=True, max_length=40)
    base_code = models.CharField('Базова валюта', max_length=8, default='UAH')
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    intro = models.TextField('Опис для сторінки пари', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        ordering = ['sort_order', 'code']
        verbose_name = 'Валютна пара'
        verbose_name_plural = 'Валютні пари'

    def __str__(self):
        return self.code


class Quote(models.Model):
    pair = models.ForeignKey(
        CurrencyPair,
        on_delete=models.CASCADE,
        related_name='quotes',
        verbose_name='Пара',
    )
    board = models.CharField(
        'Дошка',
        max_length=16,
        choices=RateBoard.choices,
        default=RateBoard.RETAIL,
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='quotes',
        verbose_name='Місто',
        null=True,
        blank=True,
        help_text='Порожньо = глобальний курс',
    )
    buy = models.DecimalField('Купівля', max_digits=14, decimal_places=4)
    sell = models.DecimalField('Продаж', max_digits=14, decimal_places=4)
    updated_at = models.DateTimeField('Оновлено', default=timezone.now)
    is_active = models.BooleanField('Активний', default=True)

    class Meta:
        ordering = ['pair__sort_order', 'pair__code']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курси'
        constraints = [
            models.UniqueConstraint(
                fields=['pair', 'board', 'city'],
                name='uniq_quote_pair_board_city',
            ),
        ]

    def __str__(self):
        city = self.city.name if self.city_id else 'глобальний'
        return f'{self.pair.code} {self.board} ({city})'

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
