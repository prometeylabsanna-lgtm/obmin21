from django.db import models


class City(models.Model):
    name = models.CharField('Назва', max_length=80)
    slug = models.SlugField('Slug', unique=True, max_length=80)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    is_active = models.BooleanField('Активне', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Місто'
        verbose_name_plural = 'Міста'

    def __str__(self):
        return self.name


class Branch(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name='Місто',
    )
    address = models.CharField('Адреса', max_length=255)
    hours = models.CharField('Графік', max_length=120, blank=True)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    lat = models.DecimalField('Широта', max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField('Довгота', max_digits=9, decimal_places=6, null=True, blank=True)
    map_url = models.URLField('Посилання на карту', blank=True)
    is_active = models.BooleanField('Активне', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Відділення'
        verbose_name_plural = 'Відділення'

    def __str__(self):
        return f'{self.city.name}: {self.address}'
