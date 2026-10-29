"""Real client POSTs to site forms → Telegram + Resend staff notifications."""

from __future__ import annotations

import io
import json
import urllib.error
from decimal import Decimal
from unittest.mock import patch

from decouple import Csv
from django.core.cache import cache
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


def _http_error_500(url='https://api.telegram.org/botx/sendMessage'):
    return urllib.error.HTTPError(url, 500, 'Server Error', hdrs={}, fp=io.BytesIO(b'fail'))


_NOTIFY_OK = dict(
    NOTIFICATIONS_ASYNC=False,
    SITE_URL='https://obmin21.test',
    TELEGRAM_BOT_TOKEN='tok-forms',
    TELEGRAM_CHAT_ID=['-1001'],
    RESEND_API_KEY='re_forms_key',
    EMAIL_FROM='Staff <from@obmin21.test>',
    NOTIFY_EMAIL_TO=['ops@obmin21.test'],
    DEFAULT_FROM_EMAIL='fallback@obmin21.test',
)

_NOTIFY_EMPTY = dict(
    NOTIFICATIONS_ASYNC=False,
    SITE_URL='https://obmin21.test',
    TELEGRAM_BOT_TOKEN='',
    TELEGRAM_CHAT_ID=[],
    RESEND_API_KEY='',
    EMAIL_FROM='',
    NOTIFY_EMAIL_TO=[],
    DEFAULT_FROM_EMAIL='',
)


class _FormsNotifyFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(
            name='Харків', slug='kharkiv-forms-notify', phone='+380991111111', sort_order=0,
        )
        cls.branch = Branch.objects.create(
            city=cls.city, address='Харків, вул. Forms 1', phone=cls.city.phone,
        )
        cls.pair = CurrencyPair.objects.create(
            code='USD', name='Долар', slug='usd-uah-forms-notify',
        )
        Quote.objects.create(
            pair=cls.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )

    def setUp(self):
        self.client.post(reverse('network:set_city'), {'city': 'kharkiv-forms-notify'})

    def _clear_site_notify(self):
        cache.delete('site_settings')
        site = SiteSettings.load()
        site.notify_email = ''
        site.notify_telegram_chat_id = ''
        site.save()
        cache.delete('site_settings')

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

    def _contact_payload(self, **overrides):
        data = {
            'name': 'Анна & Co',
            'phone': '+380991112233',
            'message': 'Питання <b>деталi</b>',
            'consent': True,
        }
        data.update(overrides)
        return data

    def _review_payload(self, **overrides):
        data = {
            'name': 'Ігор <x>',
            'text': 'Все добре <b>',
            'city_name': 'Харків',
            'phone': '+380997776655',
            'rating': '5',
            'consent': True,
        }
        data.update(overrides)
        return data

    def _post_forms(self):
        return (
            (
                'exchange',
                reverse('leads:request_modal'),
                self._exchange_payload(),
                ExchangeRequest,
                'name',
                'Олег <script>',
            ),
            (
                'contact',
                reverse('leads:contact_submit'),
                self._contact_payload(),
                ContactMessage,
                'name',
                'Анна & Co',
            ),
            (
                'review',
                reverse('reviews:review_submit'),
                self._review_payload(),
                Review,
                'name',
                'Ігор <x>',
            ),
        )


@override_settings(**_NOTIFY_OK)
class FormsNotifyConfiguredTests(_FormsNotifyFixtures):
    def test_all_forms_send_telegram_and_resend(self):
        for kind, url, payload, model, field, value in self._post_forms():
            with self.subTest(kind=kind):
                model.objects.all().delete()
                with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
                    with self.captureOnCommitCallbacks(execute=True):
                        resp = self.client.post(url, payload)
                self.assertIn(resp.status_code, (200, 302))
                self.assertEqual(model.objects.filter(**{field: value}).count(), 1)
                obj = model.objects.get(**{field: value})

                tg_calls = []
                resend_calls = []
                for call in urlopen.call_args_list:
                    req = call.args[0]
                    full_url, body, headers = _parse_request(req)
                    if 'api.telegram.org' in full_url:
                        tg_calls.append((full_url, body))
                    elif 'api.resend.com' in full_url:
                        resend_calls.append((full_url, body, headers))

                self.assertEqual(len(tg_calls), 1)
                tg_url, tg_body = tg_calls[0]
                self.assertIn('/bottok-forms/sendMessage', tg_url)
                self.assertEqual(tg_body['chat_id'], '-1001')
                self.assertEqual(tg_body['parse_mode'], 'HTML')
                self.assertIn(f'#{obj.pk}', tg_body['text'])
                if kind == 'exchange':
                    self.assertIn('&lt;script&gt;', tg_body['text'])
                    self.assertIn("Ім'я:", tg_body['text'])
                    self.assertIn('+380991234567', tg_body['text'])
                elif kind == 'contact':
                    self.assertIn('&amp;', tg_body['text'])
                    self.assertIn('&lt;b&gt;', tg_body['text'])
                    self.assertIn('Звернення', tg_body['text'])
                else:
                    self.assertIn('&lt;x&gt;', tg_body['text'])
                    self.assertIn('&lt;b&gt;', tg_body['text'])
                    self.assertIn('Новий відгук', tg_body['text'])

                self.assertEqual(len(resend_calls), 1)
                resend_url, resend_body, headers = resend_calls[0]
                self.assertEqual(resend_url, 'https://api.resend.com/emails')
                self.assertEqual(headers.get('authorization'), 'Bearer re_forms_key')
                self.assertEqual(resend_body['from'], 'Staff <from@obmin21.test>')
                self.assertEqual(resend_body['to'], ['ops@obmin21.test'])
                self.assertIn(str(obj.pk), resend_body['subject'])


@override_settings(**_NOTIFY_EMPTY)
class FormsNotifyEmptyConfigTests(_FormsNotifyFixtures):
    def test_all_forms_skip_urlopen_warn_and_save(self):
        self._clear_site_notify()
        for kind, url, payload, model, field, value in self._post_forms():
            with self.subTest(kind=kind):
                model.objects.all().delete()
                with patch('urllib.request.urlopen') as urlopen:
                    with self.assertLogs('src.core.notifications.telegram', level='WARNING') as tg_logs:
                        with self.assertLogs('src.core.notifications.resend', level='WARNING') as mail_logs:
                            with self.captureOnCommitCallbacks(execute=True):
                                resp = self.client.post(url, payload)
                self.assertIn(resp.status_code, (200, 302))
                self.assertNotEqual(resp.status_code, 500)
                self.assertEqual(model.objects.filter(**{field: value}).count(), 1)
                urlopen.assert_not_called()
                self.assertTrue(any('TELEGRAM_BOT_TOKEN' in line for line in tg_logs.output))
                self.assertTrue(
                    any(
                        'RESEND_API_KEY' in line or 'no recipients' in line or 'EMAIL_FROM' in line
                        for line in mail_logs.output
                    ),
                )


@override_settings(**_NOTIFY_OK)
class FormsNotifyFailureTests(_FormsNotifyFixtures):
    def test_urlopen_failures_still_save_no_500(self):
        errors = (
            ('timeout', TimeoutError('slow')),
            ('connection', ConnectionError('down')),
            ('http500', _http_error_500()),
        )
        for kind, url, payload, model, field, value in self._post_forms():
            for err_name, exc in errors:
                with self.subTest(kind=kind, error=err_name):
                    model.objects.all().delete()
                    unique = f'{value}-{err_name}'
                    data = dict(payload)
                    data[field] = unique
                    with patch('urllib.request.urlopen', side_effect=exc):
                        with self.captureOnCommitCallbacks(execute=True):
                            resp = self.client.post(url, data)
                    self.assertNotEqual(resp.status_code, 500)
                    self.assertIn(resp.status_code, (200, 302))
                    self.assertTrue(model.objects.filter(**{field: unique}).exists())


@override_settings(
    NOTIFICATIONS_ASYNC=False,
    TELEGRAM_BOT_TOKEN='tok-legacy',
    RESEND_API_KEY='',
    EMAIL_FROM='',
    NOTIFY_EMAIL_TO=[],
    DEFAULT_FROM_EMAIL='',
)
class LegacyTelegramChatIdTests(TestCase):
    def test_csv_single_chat_id_one_sendmessage(self):
        chats = Csv()('-100123')
        self.assertEqual(chats, ['-100123'])
        with override_settings(TELEGRAM_CHAT_ID=chats):
            with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
                from src.core.notifications.telegram import send_telegram_html

                ok = send_telegram_html('<b>legacy csv</b>')
        self.assertTrue(ok)
        self.assertEqual(urlopen.call_count, 1)
        _, body, _ = _parse_request(urlopen.call_args.args[0])
        self.assertEqual(body['chat_id'], '-100123')

    def test_plain_string_chat_id_not_iterated_by_chars(self):
        with override_settings(TELEGRAM_CHAT_ID='-100123'):
            with patch('urllib.request.urlopen', return_value=_FakeResponse()) as urlopen:
                from src.core.notifications.telegram import resolve_chat_ids, send_telegram_html

                self.assertEqual(resolve_chat_ids(), ['-100123'])
                ok = send_telegram_html('<b>legacy str</b>')
        self.assertTrue(ok)
        self.assertEqual(urlopen.call_count, 1)
        _, body, _ = _parse_request(urlopen.call_args.args[0])
        self.assertEqual(body['chat_id'], '-100123')
        chat_ids = {json.loads(c.args[0].data.decode())['chat_id'] for c in urlopen.call_args_list}
        self.assertNotIn('-', chat_ids)
        self.assertNotIn('1', chat_ids)
