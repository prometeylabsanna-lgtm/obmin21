from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from src.core.exchange_fields import mode_char, mode_text
from src.core.exchange_mode import ExchangeSafeMixin
from src.network.models import City


class RateBoard(models.TextChoices):
    RETAIL = 'retail', 'Готівка'
    CRYPTO = 'crypto', 'Крипто'


class CurrencyPair(ExchangeSafeMixin, models.Model):
    code = models.CharField('Код', max_length=16)
    name = models.CharField('Назва', max_length=80)
    slug = models.SlugField('Код у посиланні', unique=True, max_length=40)
    base_code = models.CharField('Базова валюта', max_length=8, default='UAH')
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    intro = models.TextField('Опис для сторінки пари', blank=True)
    intro_mode = mode_text('Опис для сторінки пари для режиму «Лише обмін»')
    seo_title = models.CharField('Назва для SEO', max_length=160, blank=True)
    seo_title_mode = mode_char('Назва для SEO в режимі «Лише обмін»', 160)
    seo_description = models.CharField('Опис для SEO', max_length=320, blank=True)
    seo_description_mode = mode_char('Опис для SEO в режимі «Лише обмін»', 320)
    flag_image = models.ImageField(
        'Іконка прапора',
        upload_to='flags/',
        blank=True,
        help_text='Якщо порожньо — стандартний прапор за кодом валюти.',
    )

    class Meta:
        ordering = ['sort_order', 'code']
        verbose_name = 'Валютна пара'
        verbose_name_plural = 'Валютні пари'

    FLAG_MARKS = {
        'BTC': '₿',
        'ETH': 'Ξ',
        'USDT': '₮',
        'USDC': '$',
        'BNB': 'B',
        'SOL': 'S',
        'TRX': 'T',
        'TON': 'T',
    }

    def __str__(self):
        return self.code

    @property
    def flag_code(self):
        raw = (self.code or '').upper().replace(' ', '')
        if raw in {'EURUSD', 'EUR/USD'}:
            return 'EURUSD'
        if '/' in raw:
            return raw.split('/', 1)[0]
        return raw

    @property
    def flag_mark(self):
        return self.FLAG_MARKS.get(self.flag_code, '')


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

    def clean(self):
        if not self.pair_id or not self.board:
            return
        qs = Quote.objects.filter(pair_id=self.pair_id, board=self.board)
        if self.city_id:
            qs = qs.filter(city_id=self.city_id)
        else:
            qs = qs.filter(city__isnull=True)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                'Курс для цієї пари вже є. Увімкніть існуючий рядок '
                'і змініть купівлю/продаж — не міняйте саму пару.'
            )

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
