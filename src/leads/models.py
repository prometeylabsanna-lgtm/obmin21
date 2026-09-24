from django.db import models
from django.utils import timezone

from src.network.models import Branch, City
from src.rates.models import CurrencyPair, RateBoard


class ExchangeRequest(models.Model):
    class Direction(models.TextChoices):
        BUY = 'buy', 'Купити'
        SELL = 'sell', 'Продати'

    class Status(models.TextChoices):
        NEW = 'new', 'Нова'
        IN_PROGRESS = 'in_progress', 'В обробці'
        DONE = 'done', 'Виконана'
        EXPIRED = 'expired', 'Прострочена'
        CANCELLED = 'cancelled', 'Скасована'

    name = models.CharField("Ім'я", max_length=120)
    phone = models.CharField('Телефон', max_length=32)
    messenger = models.CharField('Месенджер', max_length=80, blank=True)
    pair = models.ForeignKey(
        CurrencyPair,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name='Пара',
    )
    board = models.CharField(
        'Дошка',
        max_length=16,
        choices=RateBoard.choices,
        default=RateBoard.RETAIL,
    )
    direction = models.CharField(
        'Напрямок',
        max_length=8,
        choices=Direction.choices,
    )
    amount_give = models.DecimalField('Віддаєте', max_digits=14, decimal_places=2)
    amount_receive = models.DecimalField('Отримуєте', max_digits=14, decimal_places=2)
    rate_fixed = models.DecimalField('Зафіксований курс', max_digits=14, decimal_places=4)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='exchange_requests',
        verbose_name='Місто',
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='exchange_requests',
        verbose_name='Відділення',
    )
    consent = models.BooleanField('Згода на обробку даних', default=False)
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
    )
    expires_at = models.DateTimeField('Дійсна до')
    created_at = models.DateTimeField('Створено', default=timezone.now)
    notes = models.TextField('Нотатки', blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на обмін'
        verbose_name_plural = 'Заявки на обмін'

    def __str__(self):
        return f'{self.name} · {self.pair.code} · {self.phone}'


class ContactMessage(models.Model):
    name = models.CharField("Ім'я", max_length=120)
    phone = models.CharField('Телефон', max_length=32)
    message = models.TextField('Повідомлення')
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_messages',
        verbose_name='Місто',
    )
    consent = models.BooleanField('Згода на обробку даних', default=False)
    is_processed = models.BooleanField('Опрацьовано', default=False)
    created_at = models.DateTimeField('Створено', default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Звернення'
        verbose_name_plural = 'Звернення'

    def __str__(self):
        return f'{self.name} · {self.phone}'
