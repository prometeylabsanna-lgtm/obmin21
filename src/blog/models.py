from django.db import models
from django.utils import timezone

_UK_MONTHS = (
    '',
    'січня',
    'лютого',
    'березня',
    'квітня',
    'травня',
    'червня',
    'липня',
    'серпня',
    'вересня',
    'жовтня',
    'листопада',
    'грудня',
)

_READ_ORDER = (
    'kurs-dolara-2027',
    'dolar-chy-yevro',
    'spravzhnya-kupyura',
    'investytsiyne-zoloto',
    'kryptovalyuta-btc-usdt',
    'bezpechno-velyka-suma',
    'mizhnarodni-perekazy',
    'znosheni-kupyury',
    'kurs-kupivli-prodazhu',
    'fiksatsiya-kursu-onlain',
)


class Category(models.Model):
    name = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Slug', unique=True, max_length=80)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Категорія блогу'
        verbose_name_plural = 'Категорії блогу'

    def __str__(self):
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Чернетка'
        PUBLISHED = 'published', 'Опубліковано'

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='posts',
        verbose_name='Категорія',
    )
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Slug', unique=True, max_length=200)
    excerpt = models.TextField('Анонс', blank=True)
    body = models.TextField('Текст')
    cover = models.ImageField('Обкладинка', upload_to='blog/', blank=True)
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField('Опубліковано', null=True, blank=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)
    seo_title = models.CharField('SEO Title', max_length=160, blank=True)
    seo_description = models.CharField('SEO Description', max_length=320, blank=True)
    faq = models.TextField('FAQ (опційно)', blank=True)

    class Meta:
        ordering = ['-published_at', '-id']
        verbose_name = 'Стаття'
        verbose_name_plural = 'Статті'

    def __str__(self):
        return self.title

    def image_url(self):
        from django.contrib.staticfiles import finders
        from django.templatetags.static import static

        name = f'images/articles/{self.slug}.jpg'
        if finders.find(name):
            return static(name)
        if self.cover:
            return self.cover.url
        return static('images/service-1.png')

    def date_uk(self):
        if not self.published_at:
            return ''
        d = timezone.localtime(self.published_at)
        return f'{d.day} {_UK_MONTHS[d.month]} {d.year}'

    def reading_label(self):
        try:
            idx = _READ_ORDER.index(self.slug)
        except ValueError:
            idx = 0
        return f'{4 + (idx % 4)} хв читання'

    def publish(self):
        self.status = self.Status.PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at', 'updated_at'])
