from django.db import models


class FaqPageCopy(models.Model):
    kicker = models.CharField('Підпис над заголовком', max_length=80, default='Відповіді')
    title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='поширені запитання',
        blank=True,
    )
    lead = models.CharField(
        'Підзаголовок',
        max_length=400,
        blank=True,
        default='Короткі відповіді на те, що найчастіше запитують перед обміном.',
    )
    cta_title = models.CharField(
        'Заголовок підказки',
        max_length=120,
        default='Не знайшли',
    )
    cta_title_accent = models.CharField(
        'Акцент підказки',
        max_length=80,
        default='відповідь?',
    )
    cta_text = models.CharField(
        'Текст підказки',
        max_length=320,
        default='Консультант відповість на будь-яке питання щодня з 8:00 до 21:00.',
    )
    cta_phone = models.CharField(
        'Кнопка телефону',
        max_length=80,
        default='Зателефонувати',
    )
    cta_telegram = models.CharField(
        'Кнопка Telegram',
        max_length=80,
        default='Написати в Telegram',
    )

    class Meta:
        abstract = True
