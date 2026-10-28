import os
import re
from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.blog.models import Category, Post
from src.content.models import (
    AdvantagesPage,
    BlogPage,
    CitiesPage,
    CookiePage,
    FaqItem,
    FaqPage,
    HomePage,
    HomeStat,
    OfferPage,
    PrivacyPage,
    RatesPage,
    Service,
    ServicesPage,
)
from src.core.exchange_stopwords import STOP_WORDS
from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard
from src.reviews.models import Review as ReviewModel

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_POISON = (
    'криптовалюта переказ золото опт зношені swift bitcoin заміна usdt btc eth'
)
_CLEAN = 'Готівка у касі відділення'
_BOUND = frozenset({
    'eth', 'btc', 'bnb', 'sol', 'trx', 'ton', 'gold', 'swift', 'usdt', 'usdc',
})
_EXTRA_STOPS = ('замін',)

# стан після content 0023 (eo/cms), текст зі зведеної БД ~/Sites/Obmin21-wt-merge
OFFER_BODY_AFTER_0023 = """Ця оферта визначає умови надання послуг мережі Обмін21 через сайт, телефон і відділення.

Предмет

Ми приймаємо заявки на обмін валют та супутні послуги, зазначені на сайті.

Заявка та курс

Заявка на сайті фіксує намір клієнта. Курс і сума підтверджуються менеджером або касиром перед розрахунком.

Ідентифікація

Для операцій у межах лімітів достатньо паспорта або ID-картки. Для більших сум можуть знадобитися додаткові документи згідно з вимогами фінмоніторингу.

Відмова від операції

Ми можемо відмовити в обслуговуванні, якщо є ознаки підробки, порушення законодавства або неповні дані клієнта.

Відповідальність

Фінальні умови операції підтверджуються у відділенні. Питання щодо оферти надсилайте на контактний email у налаштуваннях сайту."""
PRIVACY_BODY_AFTER_0023 = """Ми обробляємо персональні дані (імʼя, телефон, повідомлення) виключно для обробки заявок і зворотного звʼязку.

Які дані збираємо

Контактні дані з форм на сайті, технічні журнали звернень і параметри заявки на обмін (валюта, сума, відділення).

Навіщо

Щоб підтвердити заявку, звʼязатися з вами та надати послугу в обраному відділенні.

Зберігання та передача

Дані не продаються третім особам. Передача можлива лише за законною підставою.

Ваші права

Ви можете запросити уточнення, виправлення або видалення даних, написавши на контактний email, зазначений у налаштуваннях сайту."""
COOKIE_BODY_AFTER_0023 = """Ми використовуємо файли cookie, щоб сайт працював стабільно, запам’ятовував місто та зберігав технічні налаштування сесії.

Які cookie застосовуємо

Необхідні cookie для безпеки форм і вибору міста, а також технічні журнали, що допомагають усувати збої.

Навіщо вони потрібні

Щоб показати відділення вашого міста, захистити заявки від повторної відправки і коректно відкривати сторінки на різних пристроях, зокрема в iOS Safari.

Термін зберігання

Сесійні cookie видаляються після закриття браузера. Cookie міста можуть зберігатися довше, щоб не обирати локацію щоразу.

Керування

Ви можете вимкнути cookie в налаштуваннях браузера. Частина функцій сайту тоді може працювати обмежено."""


def _clip(value, field):
    limit = getattr(field, 'max_length', None)
    if limit:
        return value[:limit]
    return value


def _poison_mode_fields(obj):
    changed = []
    for field in obj._meta.concrete_fields:
        if not field.name.endswith('_mode'):
            continue
        if not isinstance(field, models.CharField):
            continue
        base_name = field.name[:-5]
        try:
            base = obj._meta.get_field(base_name)
        except FieldDoesNotExist:
            continue
        if not isinstance(base, models.CharField):
            continue
        setattr(obj, base_name, _clip(_POISON, base))
        setattr(obj, field.name, _clip(_CLEAN, field))
        changed.extend([base_name, field.name])
    if changed:
        obj.save(update_fields=changed)


def _boundary(token):
    return (
        r'(?<![0-9a-zа-яіїєґ])'
        + re.escape(token)
        + r'(?![0-9a-zа-яіїєґ])'
    )


def stop_hit(html):
    lowered = html.lower()
    if 'bitcoin.png' in lowered:
        return 'bitcoin.png'
    if 'bitcoin.webp' in lowered:
        return 'bitcoin.webp'
    for word in (*STOP_WORDS, *_EXTRA_STOPS):
        token = word.casefold()
        if token in _BOUND:
            if re.search(_boundary(token), lowered):
                return token
            continue
        if token in lowered:
            return token
    return ''


class ExchangeOnlySiteSpiderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cache.clear()
        SiteSettings.load()
        for model in (
            HomePage,
            ServicesPage,
            AdvantagesPage,
            FaqPage,
            RatesPage,
            CitiesPage,
            BlogPage,
        ):
            _poison_mode_fields(model.load())
        OfferPage.load()
        OfferPage.objects.filter(pk=1).update(body=OFFER_BODY_AFTER_0023)
        PrivacyPage.load()
        PrivacyPage.objects.filter(pk=1).update(body=PRIVACY_BODY_AFTER_0023)
        CookiePage.load()
        CookiePage.objects.filter(pk=1).update(body=COOKIE_BODY_AFTER_0023)
        city = City.objects.create(
            name='Львів',
            slug='lviv',
            phone='+380441112233',
            sort_order=0,
        )
        _poison_mode_fields(city)
        Branch.objects.create(
            city=city,
            address='вул. Ринкова, 1',
            hours='Пн–Нд 09:00–19:00',
            phone='+380441112233',
        )
        HomeStat.objects.create(
            page=HomePage.load(),
            number='3K',
            text=_POISON,
            exchange_safe=True,
            is_active=True,
            sort_order=9,
        )
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Готівковий обмін у відділенні',
            exchange_safe=True,
            show_on_home=True,
            sort_order=1,
        )
        Service.objects.create(
            title='Грошові перекази',
            slug='groshovi-perekazy',
            short_desc=_POISON,
            exchange_safe=False,
            show_on_home=True,
            sort_order=2,
        )
        FaqItem.objects.create(
            question='Який курс долара у відділенні?',
            answer='Курс фіксується на тридцять хвилин.',
            exchange_safe=True,
            sort_order=1,
        )
        FaqItem.objects.create(
            question='Як надіслати переказ SWIFT?',
            answer=_POISON,
            exchange_safe=False,
            sort_order=2,
        )
        ReviewModel.objects.create(
            name='Олена',
            text='Обміняла долар у відділенні.',
            city_name='Львів',
            is_published=True,
            exchange_safe=True,
            published_at=timezone.now(),
        )
        ReviewModel.objects.create(
            name='Ігор',
            text=_POISON,
            is_published=True,
            exchange_safe=False,
            published_at=timezone.now(),
        )
        category = Category.objects.create(name='Каса', slug='kasa')
        Post.objects.create(
            category=category,
            title='Курс долара у касі',
            slug='kurs-u-kasi',
            excerpt='Фіксація курсу у відділенні.',
            body='Долар і євро міняють у касі за курсом відділення.',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
            exchange_safe=True,
        )
        Post.objects.create(
            category=category,
            title='Криптовалюта і перекази',
            slug='krypto-perekaz',
            excerpt=_POISON,
            body=_POISON,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
            exchange_safe=False,
        )
        usd = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd',
            exchange_safe=True,
            sort_order=1,
        )
        btc = CurrencyPair.objects.create(
            code='BTC',
            name='Bitcoin',
            slug='btc',
            intro=_POISON,
            exchange_safe=False,
            sort_order=2,
        )
        for pair, buy, sell in (
            (usd, '41.2000', '41.8000'),
            (btc, '1.5000', '1.6000'),
        ):
            Quote.objects.create(
                pair=pair,
                board=RateBoard.RETAIL,
                buy=Decimal(buy),
                sell=Decimal(sell),
            )
        cls.urls = {
            'home': reverse('core:home'),
            'services': reverse('content:services'),
            'advantages': reverse('content:advantages'),
            'faq': reverse('content:faq'),
            'contacts': reverse('content:contacts'),
            'privacy': reverse('content:privacy'),
            'offer': reverse('content:offer'),
            'cookies': reverse('content:cookies'),
            'cities': reverse('network:city_list'),
            'city': reverse('network:city_detail', kwargs={'slug': 'lviv'}),
            'rates': reverse('rates:rates_page'),
            'pair': reverse('rates:pair_detail', kwargs={'slug': 'usd'}),
            'blog': reverse('blog:post_list'),
            'post': reverse('blog:post_detail', kwargs={'slug': 'kurs-u-kasi'}),
            'reviews': reverse('reviews:review_list'),
        }

    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        cache.clear()
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={'exchange_only': enabled},
        )
        cache.clear()

    def _assert_mode_on(self, name):
        self._set_mode(True)
        url = self.urls[name]
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        hit = stop_hit(response.content.decode())
        self.assertFalse(hit, f'{url} містить {hit}')

    def test_mode_on_home(self):
        self._assert_mode_on('home')

    def test_mode_on_services(self):
        self._assert_mode_on('services')

    def test_mode_on_advantages(self):
        self._assert_mode_on('advantages')

    def test_mode_on_faq(self):
        self._assert_mode_on('faq')

    def test_mode_on_contacts(self):
        self._assert_mode_on('contacts')

    def test_mode_on_privacy(self):
        self._assert_mode_on('privacy')

    def test_mode_on_offer(self):
        self._assert_mode_on('offer')

    def test_mode_on_cookies(self):
        self._assert_mode_on('cookies')

    def test_mode_on_cities(self):
        self._assert_mode_on('cities')

    def test_mode_on_city(self):
        self._assert_mode_on('city')

    def test_mode_on_rates(self):
        self._assert_mode_on('rates')

    def test_mode_on_pair(self):
        self._assert_mode_on('pair')

    def test_mode_on_blog(self):
        self._assert_mode_on('blog')

    def test_mode_on_post(self):
        self._assert_mode_on('post')

    def test_mode_on_reviews(self):
        self._assert_mode_on('reviews')

    def test_mode_off_pages_return_200(self):
        self._set_mode(False)
        for name, url in self.urls.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, name)
