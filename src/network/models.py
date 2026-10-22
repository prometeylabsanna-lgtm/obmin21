from urllib.parse import quote_plus, urlparse

from django.core.exceptions import ValidationError
from django.db import models

from src.core.exchange_fields import mode_char

MAP_EMBED_HELP = (
    'Google Maps → Поділитися → Вбудувати карту → '
    'скопіювати значення src з коду iframe.'
)
MAP_EMBED_ERROR = (
    'Дозволено лише https-посилання Google Maps: '
    'google.com або www.google.com зі шляхом /maps, або хост maps.google.com.'
)


def _google_embed_src(query):
    return (
        'https://maps.google.com/maps?q='
        f'{quote_plus(query)}&z=15&hl=uk&output=embed'
    )


def _unsafe_map_embed_chars(value):
    return any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value)


def validate_map_embed_url(value):
    if value is None or value == '':
        return
    if not isinstance(value, str) or _unsafe_map_embed_chars(value):
        raise ValidationError(MAP_EMBED_ERROR, code='invalid')
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    path = (parsed.path or '').lower()
    scheme = (parsed.scheme or '').lower()
    allowed_path = host in {'google.com', 'www.google.com'} and path.startswith('/maps')
    allowed_host = host == 'maps.google.com'
    if scheme != 'https' or not (allowed_path or allowed_host):
        raise ValidationError(MAP_EMBED_ERROR, code='invalid')


class City(models.Model):
    name = models.CharField('Назва', max_length=80)
    name_mode = mode_char('Назва для режиму «Лише обмін»', 80)
    slug = models.SlugField('Код у посиланні', unique=True, max_length=80)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    is_active = models.BooleanField('Активне', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    seo_title = models.CharField('Назва для SEO', max_length=160, blank=True)
    seo_title_mode = mode_char('Назва для SEO в режимі «Лише обмін»', 160)
    seo_description = models.CharField('Опис для SEO', max_length=320, blank=True)
    seo_description_mode = mode_char('Опис для SEO в режимі «Лише обмін»', 320)
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
    banner_title_mode = mode_char('Заголовок банера для режиму «Лише обмін»', 80)
    banner_suffix = models.CharField(
        'Текст після назви міста',
        max_length=80,
        default='за вигідним курсом',
    )
    banner_suffix_mode = mode_char(
        'Текст після назви міста для режиму «Лише обмін»',
        80,
    )
    banner_text = models.CharField(
        'Підпис на банері',
        max_length=240,
        default='Фіксуйте курс онлайн та обмінюйте за вигідним курсом',
    )
    banner_text_mode = mode_char('Підпис на банері для режиму «Лише обмін»', 240)
    banner_button = models.CharField(
        'Текст кнопки на банері',
        max_length=80,
        default='Зафіксувати курс',
    )
    banner_button_mode = mode_char(
        'Текст кнопки на банері для режиму «Лише обмін»',
        80,
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
    map_embed_url = models.URLField(
        'URL вбудованої карти',
        blank=True,
        default='',
        max_length=2048,
        help_text=MAP_EMBED_HELP,
    )
    is_active = models.BooleanField('Активне', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Відділення'
        verbose_name_plural = 'Відділення'

    def __str__(self):
        return f'{self.city.name}: {self.address}'

    def map_embed_src(self):
        embed = (self.map_embed_url or '').strip()
        if embed:
            return embed
        if self.lat is not None and self.lng is not None:
            query = f'{format(self.lat, "f")},{format(self.lng, "f")}'
            return _google_embed_src(query)
        return _google_embed_src(f'{self.address}, Ukraine')

    def clean_fields(self, exclude=None):
        if isinstance(self.map_embed_url, str):
            self.map_embed_url = self.map_embed_url.strip()
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        try:
            validate_map_embed_url(self.map_embed_url)
        except ValidationError as exc:
            raise ValidationError({'map_embed_url': exc.messages}) from exc

    def map_route_url(self):
        if self.map_url:
            return self.map_url
        return f'https://maps.google.com/?q={quote_plus(self.address)}'


from src.network.cms_proxies import BannerCity, ContactCity, MapCity  # noqa: E402,F401
