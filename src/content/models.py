from django.db import models


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomePage(SingletonModel):
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)
    banner_exchange = models.ImageField('Банер після курсів', upload_to='home/', blank=True)
    banner_service = models.ImageField('Банер після послуг', upload_to='home/', blank=True)
    banner_cta = models.ImageField('Банер CTA', upload_to='home/', blank=True)
    cta_title = models.CharField(
        'CTA заголовок',
        max_length=160,
        default='Зафіксуй курс. Забронюй онлайн.',
    )
    seo_block_title = models.CharField(
        'SEO блок · заголовок',
        max_length=160,
        default='Обмін валют',
    )
    seo_block_body = models.TextField('SEO блок · текст', blank=True)

    class Meta:
        verbose_name = 'Головна сторінка'
        verbose_name_plural = 'Головна сторінка'

    def __str__(self):
        return 'Головна'


class RatesPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='Курси валют')
    intro = models.TextField('Вступ', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка курсів'
        verbose_name_plural = 'Сторінка курсів'

    def __str__(self):
        return self.title


class ServicesPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='Послуги')
    intro = models.TextField('Вступ', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка послуг'
        verbose_name_plural = 'Сторінка послуг'

    def __str__(self):
        return self.title


class Service(models.Model):
    title = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Slug', unique=True, max_length=80)
    short_desc = models.TextField('Короткий опис')
    body = models.TextField('Повний опис', blank=True)
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Послуга'
        verbose_name_plural = 'Послуги'

    def __str__(self):
        return self.title


class AdvantagesPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='Переваги')
    intro = models.TextField('Вступ', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

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

    audience = models.CharField('Аудиторія', max_length=16, choices=Audience.choices)
    text = models.CharField('Текст', max_length=255)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активний', default=True)

    class Meta:
        ordering = ['audience', 'sort_order', 'id']
        verbose_name = 'Пункт переваги'
        verbose_name_plural = 'Пункти переваг'

    def __str__(self):
        return f'{self.get_audience_display()}: {self.text[:40]}'


class ContactsPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='Контакти')
    intro = models.TextField('Вступ', blank=True)
    map_image = models.ImageField('Зображення карти', upload_to='contacts/', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка контактів'
        verbose_name_plural = 'Сторінка контактів'

    def __str__(self):
        return self.title


class PrivacyPage(SingletonModel):
    title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Політика конфіденційності',
    )
    body = models.TextField('Текст', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Політика конфіденційності'
        verbose_name_plural = 'Політика конфіденційності'

    def __str__(self):
        return self.title


class CitiesPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='Міста мережі')
    intro = models.TextField('Вступ', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка міст'
        verbose_name_plural = 'Сторінка міст'

    def __str__(self):
        return self.title


class FaqPage(SingletonModel):
    title = models.CharField('Заголовок', max_length=120, default='FAQ')
    intro = models.TextField('Вступ', blank=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)

    class Meta:
        verbose_name = 'Сторінка FAQ'
        verbose_name_plural = 'Сторінка FAQ'

    def __str__(self):
        return self.title


class FaqItem(models.Model):
    question = models.CharField('Питання', max_length=255)
    answer = models.TextField('Відповідь')
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активний', default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Питання FAQ'
        verbose_name_plural = 'Питання FAQ'

    def __str__(self):
        return self.question[:60]
