from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.leads.models import ExchangeRequest
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard


class Obmin21SmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city_a = City.objects.create(
            name='Харків',
            slug='kharkiv',
            phone='+380991111111',
            sort_order=0,
        )
        cls.city_b = City.objects.create(
            name='Київ',
            slug='kyiv',
            phone='+380992222222',
            sort_order=1,
        )
        cls.branch_a = Branch.objects.create(
            city=cls.city_a,
            address='Харків, вул. 1',
            phone=cls.city_a.phone,
        )
        cls.branch_b = Branch.objects.create(
            city=cls.city_b,
            address='Київ, вул. 2',
            phone=cls.city_b.phone,
        )
        cls.pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
        )
        Quote.objects.create(
            pair=cls.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )
        cat = Category.objects.create(name='Новини', slug='novyny')
        Post.objects.create(
            category=cat,
            title='Публічна',
            slug='public-post',
            body='Текст',
            status=Post.Status.PUBLISHED,
        )
        Post.objects.create(
            category=cat,
            title='Чернетка',
            slug='draft-post',
            body='Текст',
            status=Post.Status.DRAFT,
        )

    def test_home_ok(self):
        resp = self.client.get(reverse('core:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'USD')

    def test_set_city_changes_phone_and_branches(self):
        resp = self.client.post(reverse('network:set_city'), {'city': 'kyiv'})
        self.assertEqual(resp.status_code, 302)
        home = self.client.get(reverse('core:home'))
        self.assertContains(home, 'Київ')
        self.assertContains(home, 'Київ, вул. 2')

    def test_invalid_phone_does_not_create_request(self):
        before = ExchangeRequest.objects.count()
        resp = self.client.post(reverse('leads:request_modal'), {
            'name': 'Тест',
            'phone': '123',
            'pair': self.pair.pk,
            'board': RateBoard.RETAIL,
            'direction': 'sell',
            'amount_give': '100',
            'amount_receive': '4120',
            'rate_fixed': '41.20',
            'branch': self.branch_a.pk,
            'consent': True,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ExchangeRequest.objects.count(), before)

    def test_valid_request_creates_row(self):
        self.client.post(reverse('network:set_city'), {'city': 'kharkiv'})
        resp = self.client.post(reverse('leads:request_modal'), {
            'name': 'Олег',
            'phone': '+380991234567',
            'pair': self.pair.pk,
            'board': RateBoard.RETAIL,
            'direction': 'sell',
            'amount_give': '100',
            'amount_receive': '4120',
            'rate_fixed': '41.20',
            'branch': self.branch_a.pk,
            'consent': True,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Заявку прийнято')
        self.assertEqual(ExchangeRequest.objects.count(), 1)

    def test_draft_not_in_sitemap(self):
        resp = self.client.get('/sitemap.xml')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('public-post', content)
        self.assertNotIn('draft-post', content)

    def test_csrf_required_on_contact(self):
        c = Client(enforce_csrf_checks=True)
        resp = c.post(reverse('leads:contact_submit'), {
            'name': 'A',
            'phone': '+380991234567',
            'message': 'Hi',
            'consent': True,
        })
        self.assertEqual(resp.status_code, 403)
