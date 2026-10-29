import io
import json
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from src.core.models import SiteSettings
from src.leads.models import ContactMessage, ExchangeRequest
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard
from src.reviews.models import Review


class _FakeResponse:
    def __init__(self, body=b'{}'):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _parse_request(req):
    body = json.loads(req.data.decode('utf-8'))
    headers = {key.lower(): value for key, value in req.header_items()}
    return req.full_url, body, headers


@override_settings(
    NOTIFICATIONS_ASYNC=False,
    SITE_URL='https://obmin21.test',
    TELEGRAM_BOT_TOKEN='tok-test',
    TELEGRAM_CHAT_ID=['-1001', '-1002'],
    DEFAULT_FROM_EMAIL='fallback@obmin21.test',
)
class NotificationBackendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(
            name='Харків', slug='kharkiv-notify', phone='+380991111111', sort_order=0,
        )
        cls.branch = Branch.objects.create(
            city=cls.city, address='Харків, вул. 1', phone=cls.city.phone,
        )
        cls.pair = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-uah-notify')
        Quote.objects.create(
            pair=cls.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )

    def setUp(self):
        self.client.post(reverse('network:set_city'), {'city': 'kharkiv-notify'})
        mail.outbox.clear()

    def _exchange_payload(self, **overrides):
        data = {
            'name': 'Олег <script>',
            'phone': '+380991234567',
            'messenger': 'tg',
            'pair': self.pair.pk,
            'board': RateBoard.RETAIL,
            'direction': 'sell',
            'amount_give': '100',
            'amount_receive': '1',
            'rate_fixed': '1',
            'branch': self.branch.pk,
            'consent': True,
        }
        data.update(overrides)
        return data

    def test_telegram_on_exchange_post(self):
        with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(reverse('leads:request_modal'), self._exchange_payload())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ExchangeRequest.objects.count(), 1)
        obj = ExchangeRequest.objects.get()
        self.assertEqual(len(mail.outbox), 0)

        calls = urlopen.call_args_list
        self.assertEqual(len(calls), 2)

        tg_calls = []
        for call in calls:
            req = call.args[0]
            url, body, headers = _parse_request(req)
            self.assertIn('api.telegram.org', url)
            tg_calls.append((url, body))

        self.assertEqual(len(tg_calls), 2)
        chat_ids = {body['chat_id'] for _, body in tg_calls}
        self.assertEqual(chat_ids, {'-1001', '-1002'})
        for url, body in tg_calls:
            self.assertIn('/bottok-test/sendMessage', url)
            self.assertEqual(body['parse_mode'], 'HTML')
            self.assertIn('&lt;script&gt;', body['text'])
            self.assertIn(f'#{obj.pk}', body['text'])
            self.assertIn("Ім'я:", body['text'])

    def test_contact_and_review_posts_notify(self):
        with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                contact = self.client.post(reverse('leads:contact_submit'), {
                    'name': 'Анна',
                    'phone': '+380991112233',
                    'message': 'Питання & деталі',
                    'consent': True,
                })
                review = self.client.post(reverse('reviews:review_submit'), {
                    'name': 'Ігор',
                    'text': 'Все добре <b>',
                    'city_name': 'Харків',
                    'phone': '+380997776655',
                    'rating': '5',
                    'consent': True,
                })
        self.assertEqual(contact.status_code, 200)
        self.assertEqual(review.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

        texts = []
        for call in urlopen.call_args_list:
            req = call.args[0]
            url, body, _ = _parse_request(req)
            if 'api.telegram.org' in url:
                texts.append(body['text'])
        joined = '\n'.join(texts)
        self.assertIn('Звернення', joined)
        self.assertIn('Питання &amp; деталі', joined)
        self.assertIn('Новий відгук', joined)
        self.assertIn('&lt;b&gt;', joined)

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_missing_config_no_request_warning_and_saved(self):
        with patch('urllib.request.urlopen') as urlopen:
            with self.assertLogs('src.core.notifications.telegram', level='WARNING') as tg_logs:
                with self.captureOnCommitCallbacks(execute=True):
                    resp = self.client.post(
                        reverse('leads:request_modal'),
                        self._exchange_payload(name='Без ключів'),
                    )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ExchangeRequest.objects.filter(name='Без ключів').count(), 1)
        urlopen.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any('TELEGRAM_BOT_TOKEN' in line for line in tg_logs.output))

    def test_urlopen_exception_still_saves(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError('slow')):
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(reverse('leads:request_modal'), self._exchange_payload(
                    name='Таймаут',
                    phone='+380998887766',
                ))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ExchangeRequest.objects.filter(name='Таймаут').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_urlopen_generic_exception_still_saves_contact(self):
        with patch('urllib.request.urlopen', side_effect=Exception('boom')):
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(reverse('leads:contact_submit'), {
                    'name': 'Помилка',
                    'phone': '+380991122334',
                    'message': 'текст',
                    'consent': True,
                })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ContactMessage.objects.filter(name='Помилка').exists())
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID=[])
    def test_telegram_fallback_site_settings_chat(self):
        from django.core.cache import cache

        cache.delete('site_settings')
        site = SiteSettings.load()
        site.notify_telegram_chat_id = '-999'
        site.save()
        cache.delete('site_settings')
        with override_settings(TELEGRAM_BOT_TOKEN='tok-fb'):
            with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
                from src.core.notifications.telegram import send_telegram_html
                ok = send_telegram_html('<b>hi</b>')
        self.assertTrue(ok)
        req = urlopen.call_args.args[0]
        _, body, _ = _parse_request(req)
        self.assertEqual(body['chat_id'], '-999')


@override_settings(
    NOTIFICATIONS_ASYNC=False,
    TELEGRAM_BOT_TOKEN='cmd-token-secret',
    TELEGRAM_CHAT_ID=['-1'],
)
class TestNotificationsCommandTests(TestCase):
    def test_command_ok_and_secrets_not_printed(self):
        with patch('urllib.request.urlopen', return_value=_FakeResponse()):
            out = io.StringIO()
            call_command('test_notifications', stdout=out)
        text = out.getvalue()
        self.assertIn('Telegram: OK', text)
        self.assertNotIn('Email:', text)
        self.assertNotIn('cmd-token-secret', text)

    def test_command_telegram_flag(self):
        with patch('urllib.request.urlopen', return_value=_FakeResponse()):
            out = io.StringIO()
            call_command('test_notifications', '--telegram', stdout=out)
        text = out.getvalue()
        self.assertIn('Telegram: OK', text)
        self.assertNotIn('cmd-token-secret', text)

    def test_command_fail(self):
        with patch('urllib.request.urlopen', side_effect=Exception('nope')):
            out = io.StringIO()
            call_command('test_notifications', '--telegram', stdout=out)
        text = out.getvalue()
        self.assertIn('Telegram: FAIL', text)
        self.assertNotIn('cmd-token-secret', text)
