from django.db import models
from django.utils import timezone


class Review(models.Model):
    name = models.CharField("Ім'я", max_length=120)
    text = models.TextField('Текст')
    city_name = models.CharField('Місто (текст)', max_length=80, blank=True)
    is_published = models.BooleanField('Опубліковано', default=False)
    consent = models.BooleanField('Згода', default=False)
    created_at = models.DateTimeField('Створено', default=timezone.now)
    published_at = models.DateTimeField('Опубліковано о', null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'

    def __str__(self):
        return f'{self.name}: {self.text[:40]}'

    @property
    def initial(self):
        return (self.name[:1] or '?').upper()
