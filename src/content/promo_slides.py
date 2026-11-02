from __future__ import annotations

from django.db import models

from src.core.exchange_mode import ExchangeSafeMixin

LINK_RATES = 'rates'
LINK_TELEGRAM = 'telegram'
LINK_SERVICES = 'services'
LINK_MODAL = 'modal'

LINK_CHOICES = (
    (LINK_RATES, 'Сторінка курсів'),
    (LINK_TELEGRAM, 'Telegram'),
    (LINK_SERVICES, 'Сторінка послуг'),
    (LINK_MODAL, 'Форма заявки'),
)

FULL_FIRST_TITLE = 'Вигідний курс на'
LEGACY_FIRST_TITLE = 'Вигідний курс'

SLIDE_SPECS = (
    {
        'code': 'usd-eur',
        'sort_order': 0,
        'exchange_safe': True,
        'title': FULL_FIRST_TITLE,
        'title_accent': 'USD та EUR',
        'text': 'Обмінюйте валюту за актуальним курсом без зайвих кроків',
        'button_label': 'Обрати валюту',
        'image_path': 'images/bills.png',
        'dot_label': 'USD та EUR',
        'link_kind': LINK_RATES,
    },
    {
        'code': 'crypto',
        'sort_order': 1,
        'exchange_safe': False,
        'title': 'USDT, BTC, ETH',
        'title_accent': 'на готівку',
        'text': (
            'Обмін криптовалюти від наших партнерів. '
            'Менеджер розрахує курс і розповість про умови'
        ),
        'button_label': 'Написати менеджеру',
        'image_path': 'images/coins.png',
        'dot_label': 'Криптовалюта',
        'link_kind': LINK_TELEGRAM,
    },
    {
        'code': 'transfers',
        'sort_order': 2,
        'exchange_safe': False,
        'title': 'Грошові перекази',
        'title_accent': 'по Україні та світу',
        'text': 'Надсилайте гроші рідним готівкою або на картку отримувача',
        'button_label': 'Детальніше',
        'image_path': 'images/promo-transfers.png',
        'dot_label': 'Перекази',
        'link_kind': LINK_SERVICES,
    },
    {
        'code': 'swift',
        'sort_order': 3,
        'exchange_safe': False,
        'title': 'SWIFT-перекази',
        'title_accent': 'за кордон',
        'text': 'Міжнародні перекази на рахунки в банках понад 100 країн',
        'button_label': 'Зробити заявку',
        'image_path': 'images/promo-swift.png',
        'dot_label': 'SWIFT',
        'link_kind': LINK_MODAL,
    },
)


class HomePromoSlide(ExchangeSafeMixin, models.Model):
    page = models.ForeignKey(
        'content.HomePage',
        verbose_name='Головна',
        related_name='promo_slides',
        on_delete=models.CASCADE,
    )
    code = models.CharField(
        'Код',
        max_length=40,
        blank=True,
        help_text='Службовий код. Для базових слайдів не змінюйте.',
    )
    title = models.CharField('Заголовок', max_length=120)
    title_accent = models.CharField('Акцент у заголовку', max_length=80, blank=True)
    text = models.TextField('Текст', blank=True)
    button_label = models.CharField('Текст кнопки', max_length=80, blank=True)
    image = models.ImageField('Фото', upload_to='home/promo/', blank=True)
    image_path = models.CharField(
        'Шлях до картинки',
        max_length=180,
        blank=True,
        help_text='Файл у static, якщо фото не завантажено. Наприклад images/bills.png.',
    )
    link_kind = models.CharField(
        'Куди веде слайд',
        max_length=20,
        choices=LINK_CHOICES,
        default=LINK_RATES,
    )
    dot_label = models.CharField('Підпис крапки', max_length=80, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показувати', default=True)

    class Meta:
        verbose_name = 'Слайд вигідного курсу'
        verbose_name_plural = 'Слайди вигідного курсу'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['page', 'code'],
                name='content_promo_slide_code',
            ),
        ]

    def __str__(self):
        return self.title or self.code or 'Слайд'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'slide-{self.sort_order}'
        super().save(*args, **kwargs)


def _write_full_first_title(home, slide, schema_editor):
    from src.core.deploy_seed import migration_context

    if not migration_context(schema_editor):
        return
    updates = []
    if (getattr(home, 'promo_title', '') or '').strip() == LEGACY_FIRST_TITLE:
        home.promo_title = FULL_FIRST_TITLE
        updates.append('promo_title')
    if updates:
        home.save(update_fields=updates)
    if slide is None:
        return
    title = (slide.title or '').strip()
    if title in ('', LEGACY_FIRST_TITLE):
        slide.title = FULL_FIRST_TITLE
        slide.save(update_fields=['title'])


def fill_promo_slides(apps, schema_editor):
    Slide = apps.get_model('content', 'HomePromoSlide')
    Home = apps.get_model('content', 'HomePage')
    home, _ = Home.objects.get_or_create(pk=1)
    for spec in SLIDE_SPECS:
        if Slide.objects.filter(page_id=home.pk, code=spec['code']).exists():
            continue
        Slide.objects.create(page_id=home.pk, **spec)
    first = Slide.objects.filter(page_id=home.pk, code='usd-eur').first()
    _write_full_first_title(home, first, schema_editor)


def _filled(value, fallback):
    text = (value or '').strip()
    return text if text else (fallback or '')


def slides_for_home(page):
    from django.urls import reverse

    from src.core.models import SiteSettings
    from src.core.phones import safe_telegram_url

    site = SiteSettings.load()
    telegram = safe_telegram_url(site.telegram_url)
    hrefs = {
        LINK_RATES: reverse('rates:rates_page'),
        LINK_SERVICES: reverse('content:services'),
        LINK_MODAL: reverse('leads:contact_modal'),
        LINK_TELEGRAM: telegram,
    }
    rows = []
    slides = (
        HomePromoSlide.objects.filter(page=page, is_active=True)
        .visible()
        .order_by('sort_order', 'id')
    )
    for slide in slides:
        title = slide.title
        accent = slide.title_accent
        text = slide.text
        button = slide.button_label
        dot_label = slide.dot_label
        image_field = slide.image if getattr(slide.image, 'name', '') else None
        image_path = '' if image_field else slide.image_path
        if slide.code == 'usd-eur':
            title = _filled(page.promo_title, slide.title)
            accent = _filled(page.promo_title_accent, slide.title_accent)
            text = _filled(page.promo_text, slide.text)
            button = _filled(page.promo_button, slide.button_label)
            dot_label = _filled(page.promo_kicker, slide.dot_label)
            if getattr(page.promo_image, 'name', ''):
                image_field = page.promo_image
                image_path = ''
        rows.append({
            'title': title,
            'accent': accent,
            'text': text,
            'button': button,
            'dot_label': dot_label,
            'image_field': image_field,
            'image_path': image_path,
            'href': hrefs.get(slide.link_kind, ''),
            'blank': slide.link_kind == LINK_TELEGRAM,
            'modal': slide.link_kind == LINK_MODAL,
        })
    return rows
