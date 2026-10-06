from django.db import models
from urllib.parse import quote_plus


class City(models.Model):
    name = models.CharField('Назва', max_length=80)
    slug = models.SlugField('Код у посиланні', unique=True, max_length=80)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    is_active = models.BooleanField('Активне', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    seo_title = models.CharField('Назва для SEO', max_length=160, blank=True)
    seo_description = models.CharField('Опис для SEO', max_length=320, blank=True)
    banner_image = models.ImageField(
        'Фото банера на головній',
        upload_to='cities/',
        blank=True,
        help_text='Якщо порожньо — стандартне фото міста.',
    )
    banner_title = models.CharField(
        'Заголовок банера',
        max_length=80,
        default='Обмін валют',
    )
    banner_suffix = models.CharField(
        'Текст після назви міста',
        max_length=80,
        default='за вигідним курсом',
    )
    banner_text = models.CharField(
        'Підпис на банері',
        max_length=240,
        default='Фіксуйте курс онлайн та обмінюйте за вигідним курсом',
    )
    banner_button = models.CharField(
        'Текст кнопки на банері',
        max_length=80,
        default='Зафіксувати курс',
    )

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Місто'
        verbose_name_plural = 'Міста'

    def __str__(self):
        return self.name

    CITY_IN = {
        'kyiv': 'у Києві',
        'kharkiv': 'у Харкові',
        'dnipro': 'у Дніпрі',
        'odesa': 'в Одесі',
        'lviv': 'у Львові',
        'zaporizhzhia': 'у Запоріжжі',
        'vinnytsia': 'у Вінниці',
        'mykolaiv': 'у Миколаєві',
        'khmelnytskyi': 'у Хмельницькому',
        'rivne': 'у Рівному',
        'cherkasy': 'у Черкасах',
    }

    @property
    def name_in(self):
        return self.CITY_IN.get(self.slug, f'у {self.name}')

    @property
    def hero_image(self):
        return f'images/hero-{self.slug}.jpg'

    def banner_src(self):
        if self.banner_image:
            try:
                return self.banner_image.url
            except ValueError:
                pass
        from django.contrib.staticfiles import finders
        from django.templatetags.static import static

        name = f'images/hero-{self.slug}.jpg'
        if finders.find(name):
            return static(name)
        return static('images/hero-kyiv.jpg')


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

    def map_embed_src(self):
        q = quote_plus(f'{self.address}, Ukraine')
        return f'https://maps.google.com/maps?q={q}&z=15&hl=uk&output=embed'

    def map_route_url(self):
        if self.map_url:
            return self.map_url
        return f'https://maps.google.com/?q={quote_plus(self.address)}'


from src.network.cms_proxies import BannerCity, ContactCity, MapCity  # noqa: E402,F401
