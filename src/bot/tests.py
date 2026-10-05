from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from src.bot.models import BotSession, TelegramProfile
from src.bot.services import parse_amount, quote_amounts, submit_exchange, upsert_profile
from src.bot.states import BotState
from src.leads.models import ExchangeRequest
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard


class BotServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name='Харків', slug='kharkiv-bot')
        cls.branch = Branch.objects.create(city=cls.city, address='Харків, вул. 1')
        cls.pair = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-uah-bot')
        Quote.objects.create(
            pair=cls.pair,
            board=RateBoard.RETAIL,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )

    def test_parse_amount(self):
        self.assertEqual(parse_amount('1 000,5'), Decimal('1000.50'))
        self.assertIsNone(parse_amount('-1'))
        self.assertIsNone(parse_amount('abc'))

    def test_quote_sell_and_buy(self):
        sell = quote_amounts(self.pair, self.city, 'sell', Decimal('100'))
        self.assertEqual(sell['amount_receive'], Decimal('4120.00'))
        buy = quote_amounts(self.pair, self.city, 'buy', Decimal('4160'))
        self.assertEqual(buy['amount_receive'], Decimal('100.00'))

    @patch('src.leads.services._send_telegram')
    @patch('src.leads.services._send_email')
    def test_submit_exchange(self, _email, _tg):
        user = SimpleNamespace(id=111, username='u1', first_name='Іван', last_name='')
        profile = upsert_profile(user)
        obj = submit_exchange(
            profile.chat_id,
            profile,
            {
                'city_id': self.city.pk,
                'pair_id': self.pair.pk,
                'direction': 'sell',
                'amount_give': '100',
                'branch_id': self.branch.pk,
                'name': 'Іван Тест',
                'phone': '+380991112233',
            },
        )
        self.assertEqual(obj.source, ExchangeRequest.Source.TELEGRAM)
        self.assertEqual(obj.telegram_chat_id, '111')
        self.assertEqual(obj.amount_receive, Decimal('4120.00'))


@override_settings(
    TELEGRAM_WEBHOOK_SECRET='test-secret',
    TELEGRAM_BOT_TOKEN='123:abc',
)
class BotWebhookTests(TestCase):
    def test_forbidden_without_secret(self):
        url = reverse('bot:webhook')
        response = self.client.post(url, data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_ok_with_secret_even_if_payload_bad(self):
        url = reverse('bot:webhook')
        response = self.client.post(
            url,
            data='not-json',
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='test-secret',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})

    def test_blocked_user_skipped(self):
        TelegramProfile.objects.create(chat_id='99', is_blocked=True)
        payload = '{"update_id":1,"message":{"message_id":1,"date":1,"chat":{"id":99,"type":"private"},"from":{"id":99,"is_bot":false,"first_name":"X"},"text":"/start"}}'
        url = reverse('bot:webhook')
        with patch('src.bot.views.get_bot') as mocked:
            response = self.client.post(
                url,
                data=payload,
                content_type='application/json',
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='test-secret',
            )
        self.assertEqual(response.status_code, 200)
        mocked.assert_not_called()

    def test_session_defaults(self):
        session, created = BotSession.objects.get_or_create(chat_id='5')
        self.assertTrue(created)
        self.assertEqual(session.state, BotState.IDLE)


class WebChatTests(TestCase):
    def test_log_starts_bot(self):
        url = reverse('bot:chat_log')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Обмін21')
        self.assertContains(response, 'Курси')

    def test_send_and_callback(self):
        self.client.get(reverse('bot:chat_log'))
        send = self.client.post(reverse('bot:chat_send'), {'text': 'курси'})
        self.assertEqual(send.status_code, 200)
        cb = self.client.post(
            reverse('bot:chat_callback'),
            {'data': 'mn:ex', 'label': 'Заявка'},
        )
        self.assertEqual(cb.status_code, 200)
