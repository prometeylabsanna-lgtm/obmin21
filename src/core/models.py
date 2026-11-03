from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

from src.core.contact_validators import (
    display_ua_phone,
    normalize_telegram_url,
    validate_ua_phone_or_blank,
)

from src.core.colors import (
    ACCENT_DEFAULT,
    ACCENT_HOVER_DEFAULT,
    COLOR_HELP,
    hex_color_validator,
)
from src.core.theme import bump_theme_cache


class SiteSettings(models.Model):
    site_name = models.CharField('Назва сайту', max_length=120, default='Обмін21')
    logo_text = models.CharField('Текст логотипу', max_length=40, default='ОБМІН')
    logo_accent = models.CharField('Акцент логотипу', max_length=10, default='21')
    header_logo = models.ImageField(
        'Логотип у шапці',
        upload_to='chrome/',
        blank=True,
        help_text='Якщо порожньо — лишається стандартний логотип.',
    )
    footer_logo = models.ImageField(
        'Логотип у підвалі',
        upload_to='chrome/',
        blank=True,
        help_text='Якщо порожньо — лишається стандартний логотип.',
    )
    telegram_url = models.URLField('Посилання Telegram', blank=True)
    youtube_url = models.URLField('Посилання YouTube', blank=True)
    instagram_url = models.URLField('Посилання Instagram', blank=True)
    facebook_url = models.URLField('Посилання Facebook', blank=True)
    rate_hold_minutes = models.PositiveIntegerField(
        'Хвилин фіксації курсу',
        default=30,
    )
    exchange_only = models.BooleanField(
        'Лише обмін валют',
        default=False,
        help_text=(
            'Увімкнено — на сайті тимчасово лишається лише обмін валют. '
            'Кнопка на цій сторінці вмикає і вимикає режим.'
        ),
    )
    hidden_page_status = models.PositiveSmallIntegerField(
        'Відповідь для прихованих сторінок',
        choices=(
            (503, '503 — тимчасово недоступно'),
            (404, '404 — сторінку не знайдено'),
        ),
        default=503,
        help_text=(
            '503 каже Google, що сторінка на паузі і її треба тримати в пошуку. '
            '404 — якщо режим триває довше ніж один-два тижні.'
        ),
    )
    retry_after_seconds = models.PositiveIntegerField(
        'Retry-After, секунд',
        default=86400,
        help_text='Скільки секунд зачекати перед повторним візитом. 86400 — одна доба.',
    )
    exchange_only_since = models.DateTimeField(
        'Режим «Лише обмін» увімкнено з',
        null=True,
        blank=True,
        help_text='Порожнє — режим вимкнено або час ще не зафіксовано.',
    )
    notify_email = models.EmailField('Email для сповіщень', blank=True)
    notify_telegram_chat_id = models.CharField(
        'Номер чату Telegram для сповіщень',
        max_length=64,
        blank=True,
    )
    default_phone = models.CharField(
        'Телефон, якщо місто не обрано',
        max_length=32,
        blank=True,
        validators=[validate_ua_phone_or_blank],
    )
    footer_copy = models.CharField(
        'Рядок копірайту внизу',
        max_length=120,
        default='© 2026. Обмін21. Усі права захищені',
    )
    header_cta_enabled = models.BooleanField(
        'Показувати кнопку заявки в шапці',
        default=True,
    )
    header_cta_label = models.CharField(
        'Текст кнопки заявки в шапці',
        max_length=40,
        default='Зробити заявку',
        help_text='Кнопка відкриває форму заявки. Порожньо — «Зробити заявку».',
    )
    favicon = models.FileField(
        'Іконка сайту (favicon .ico/.png/.svg)',
        upload_to='chrome/icons/',
        blank=True,
        help_text='Якщо порожньо — стандартна іконка Обмін21.',
    )
    favicon_png = models.ImageField(
        'Іконка PNG 48×48',
        upload_to='chrome/icons/',
        blank=True,
        help_text='Квадратна PNG, щонайменше 48×48. Порожньо — стандартна.',
    )
    apple_touch_icon = models.ImageField(
        'Іконка для iPhone (180×180)',
        upload_to='chrome/icons/',
        blank=True,
    )
    app_icon = models.ImageField(
        'Іконка застосунку (512×512)',
        upload_to='chrome/icons/',
        blank=True,
        help_text='Для site.webmanifest. Порожньо — стандартні 192/512.',
    )
    manifest_name = models.CharField('Назва в manifest', max_length=60, default='Обмін21')
    manifest_short_name = models.CharField('Коротка назва в manifest', max_length=30, default='Обмін21')
    theme_color = models.CharField(
        'Колір теми браузера',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    manifest_background_color = models.CharField(
        'Колір фону manifest',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_bg = models.CharField(
        'Колір фону шапки',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_text = models.CharField(
        'Колір тексту шапки',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_accent = models.CharField(
        'Колір акценту шапки',
        max_length=7,
        default=ACCENT_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    header_color_highlight = models.CharField(
        'Колір підсвітки шапки',
        max_length=7,
        default=ACCENT_HOVER_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_bg = models.CharField(
        'Колір фону підвалу',
        max_length=7,
        default='#052145',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_text = models.CharField(
        'Колір тексту підвалу',
        max_length=7,
        default='#ffffff',
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_accent = models.CharField(
        'Колір акценту підвалу',
        max_length=7,
        default=ACCENT_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )
    footer_color_highlight = models.CharField(
        'Колір підсвітки підвалу',
        max_length=7,
        default=ACCENT_HOVER_DEFAULT,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )

    class Meta:
        verbose_name = 'Загальні налаштування'
        verbose_name_plural = 'Загальні налаштування'

    def __str__(self):
        return self.site_name

    def clean(self):
        super().clean()
        self.default_phone = display_ua_phone(self.default_phone)
        if (self.telegram_url or '').strip():
            self.telegram_url = normalize_telegram_url(self.telegram_url)

    def clean_fields(self, exclude=None):
        if (self.telegram_url or '').strip():
            try:
                self.telegram_url = normalize_telegram_url(self.telegram_url)
            except ValidationError as exc:
                raise ValidationError({'telegram_url': exc.messages}) from exc
        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('site_settings')
        bump_theme_cache()

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        cached = cache.get('site_settings')
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set('site_settings', obj, 300)
        return obj


class HeaderSettings(SiteSettings):
    class Meta:
        proxy = True
        verbose_name = 'Шапка сайту'
        verbose_name_plural = 'Шапка сайту'


class FooterSettings(SiteSettings):
    class Meta:
        proxy = True
        verbose_name = 'Підвал сайту'
        verbose_name_plural = 'Підвал сайту'


class ExchangeModeLog(models.Model):
    class Source(models.TextChoices):
        ADMIN = 'admin', 'Адмінка'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exchange_mode_logs',
        verbose_name='Користувач',
    )
    created_at = models.DateTimeField('Коли', auto_now_add=True, db_index=True)
    from_value = models.BooleanField('Було')
    to_value = models.BooleanField('Стало')
    source = models.CharField(
        'Джерело',
        max_length=16,
        choices=Source.choices,
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Запис журналу режиму'
        verbose_name_plural = 'Журнал режиму «Лише обмін»'

    def __str__(self):
        from src.core.timefmt import local_fmt

        moment = local_fmt(self.created_at, '%Y-%m-%d %H:%M')
        return f'{moment}: {self.from_value} → {self.to_value}'


# --- Навігація шапки та колонки підвалу (CMS) ---

class SitePage(models.TextChoices):
    HOME = 'core:home', 'Головна'
    SERVICES = 'content:services', 'Послуги'
    ADVANTAGES = 'content:advantages', 'Переваги'
    FAQ = 'content:faq', 'FAQ'
    BLOG = 'blog:post_list', 'Блог'
    CONTACTS = 'content:contacts', 'Контакти'
    REVIEWS = 'reviews:review_list', 'Відгуки'
    RATES = 'rates:rates_page', 'Курси валют'
    CITIES = 'network:city_list', 'Міста'
    PRIVACY = 'content:privacy', 'Політика конфіденційності'
    OFFER = 'content:offer', 'Публічна оферта'
    COOKIES = 'content:cookies', 'Політика cookie'


LINK_HELP = 'Оберіть сторінку сайту або вкажіть власне посилання (/шлях/ чи https://…).'


class _LinkMixin(models.Model):
    label = models.CharField('Назва', max_length=80)
    page = models.CharField(
        'Сторінка сайту',
        max_length=40,
        choices=SitePage.choices,
        blank=True,
        help_text=LINK_HELP,
    )
    url = models.CharField('Власне посилання', max_length=300, blank=True)
    open_new_tab = models.BooleanField('Відкривати в новій вкладці', default=False)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати', default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        url = (self.url or '').strip()
        if not self.page and not url:
            raise ValidationError({'page': 'Оберіть сторінку або вкажіть посилання.'})
        if url and not (url.startswith('/') or url.startswith(('https://', 'http://', 'tel:', 'mailto:', '#'))):
            raise ValidationError({'url': 'Посилання має починатися з /, https://, tel: або mailto:.'})
        self.url = url

    @property
    def href(self):
        from django.urls import NoReverseMatch, reverse

        if self.page:
            try:
                return reverse(self.page)
            except NoReverseMatch:
                return ''
        return (self.url or '').strip()


class HeaderMenuItem(_LinkMixin):
    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name='header_menu_items',
        default=1,
        db_constraint=False,  # singleton pk=1; сід меню не створює рядок налаштувань
        verbose_name='Налаштування',
    )
    show_desktop = models.BooleanField('У шапці (комп’ютер)', default=True)
    show_mobile = models.BooleanField('У мобільному меню', default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Пункт меню шапки'
        verbose_name_plural = 'Меню шапки'


class FooterColumn(models.Model):
    class Kind(models.TextChoices):
        LINKS = 'links', 'Посилання (задаються нижче)'
        SERVICES = 'services', 'Послуги (автоматично з розділу «Послуги»)'

    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name='footer_columns',
        default=1,
        db_constraint=False,  # singleton pk=1; сід меню не створює рядок налаштувань
        verbose_name='Налаштування',
    )
    title = models.CharField('Заголовок колонки', max_length=80)
    kind = models.CharField('Вміст', max_length=16, choices=Kind.choices, default=Kind.LINKS)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати', default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Колонка підвалу'
        verbose_name_plural = 'Колонки підвалу'

    def __str__(self):
        return self.title


class FooterLink(_LinkMixin):
    column = models.ForeignKey(
        FooterColumn,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='Колонка',
    )

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Посилання підвалу'
        verbose_name_plural = 'Посилання підвалу'
