from django.db import models
from django.utils import timezone

from src.network.models import City


class TelegramProfile(models.Model):
    chat_id = models.CharField('ID чату', max_length=32, unique=True, db_index=True)
    username = models.CharField('Нікнейм', max_length=64, blank=True)
    first_name = models.CharField("Ім'я в Telegram", max_length=128, blank=True)
    last_name = models.CharField('Прізвище в Telegram', max_length=128, blank=True)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    display_name = models.CharField("Ім'я для заявок", max_length=120, blank=True)
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='telegram_profiles',
        verbose_name='Місто',
    )
    is_blocked = models.BooleanField('Заблокований', default=False)
    created_at = models.DateTimeField('Створено', default=timezone.now)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Користувач бота'
        verbose_name_plural = 'Користувачі бота'

    def __str__(self):
        label = self.username or self.display_name or self.first_name or self.chat_id
        return f'{label} ({self.chat_id})'


class BotSession(models.Model):
    chat_id = models.CharField('ID чату', max_length=32, unique=True, db_index=True)
    state = models.CharField('Стан FSM', max_length=32, default='idle')
    data = models.JSONField('Дані сценарію', default=dict, blank=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Сесія бота'
        verbose_name_plural = 'Сесії бота'

    def __str__(self):
        return f'{self.chat_id} · {self.state}'


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'Користувач'
        BOT = 'bot', 'Бот'

    chat_id = models.CharField('ID чату', max_length=32, db_index=True)
    role = models.CharField('Роль', max_length=8, choices=Role.choices)
    text = models.TextField('Текст')
    buttons = models.JSONField('Кнопки', default=list, blank=True)
    created_at = models.DateTimeField('Створено', default=timezone.now)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Повідомлення чату'
        verbose_name_plural = 'Повідомлення чату'

    def __str__(self):
        return f'{self.chat_id} · {self.role}'
