from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from src.core.models import SiteSettings
from src.core.phones import phone_tel, safe_telegram_url
from src.network.models import Branch, City

_PAGES = (
    'core:home',
    'content:contacts',
    'content:faq',
    'rates:rates_page',
    'leads:contact_modal',
    'leads:calc_modal',
)


class SafeTelegramTests(SimpleTestCase):
    def test_accepts_nick_urls(self):
        for url in (
            'https://t.me/obmin21',
            'https://telegram.me/obmin21',
            'https://t.me/s/Obmin_Desk?start=1',
        ):
            self.assertEqual(safe_telegram_url(url), url)

    def test_rejects_empty_nick(self):
        for url in ('', '   ', 'https://t.me/', 'https://t.me', 'https://telegram.me/'):
            self.assertEqual(safe_telegram_url(url), '')

    def test_short_phone_has_no_tel(self):
        self.assertEqual(phone_tel(''), '')
        self.assertEqual(phone_tel('abc'), '')
        self.assertEqual(phone_tel('123456'), '')
        self.assertEqual(phone_tel('+38 099 222-22-22'), '+380992222222')


class EmptyContactLinksTests(TestCase):
    def setUp(self):
        cache.clear()
        self.city = City.objects.create(
            name='Львів',
            slug='lviv-empty-links',
            sort_order=0,
        )

    def tearDown(self):
        cache.clear()

    def _apply(self, phone, telegram):
        site = SiteSettings.load()
        site.default_phone = ''
        site.telegram_url = telegram
        site.save()
        Branch.objects.update(is_active=False)
        City.objects.update(is_active=False)
        cache.clear()
        self.assertIn(phone, ('', 'abc'))

    def test_without_branch_phone_omitted_telegram_is_obmin21(self):
        pages = [reverse(name) for name in _PAGES]
        pages.append(reverse('rates:rates_page') + '?board=crypto')
        for telegram in ('', 'https://t.me/'):
            for phone in ('', 'abc'):
                self._apply(phone, telegram)
                for url in pages:
                    response = self.client.get(url)
                    html = response.content.decode()
                    label = f'{telegram!r} {phone!r} {url}'
                    self.assertEqual(response.status_code, 200, label)
                    self.assertIn('https://t.me/obmin21', html, label)
                    self.assertNotIn('href="https://t.me/"', html, label)
                    self.assertNotIn('href="tel:"', html, label)
                    self.assertNotIn('href="tel:abc"', html, label)
