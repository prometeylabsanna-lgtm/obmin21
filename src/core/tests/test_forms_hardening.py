from django.core.cache import cache
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from src.core.phones import normalize_ua_phone
from src.core.rate_limit import allow_request, client_ip
from src.leads.forms import ContactMessageForm
from src.leads.models import ContactMessage
from src.network.models import City
from src.reviews.forms import ReviewForm
from src.reviews.models import Review


class UaPhoneNormalizeTests(TestCase):
    def test_normalizes_common_formats(self):
        cases = (
            ('+380991234567', '+380991234567'),
            ('380991234567', '+380991234567'),
            ('0991234567', '+380991234567'),
            ('+380 99 123-45-67', '+380991234567'),
            ('(099) 123 45 67', '+380991234567'),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_ua_phone(raw), expected)

    def test_rejects_invalid(self):
        for raw in ('abc', '123', '+1234567890', '+38099123456', ''):
            with self.subTest(raw=raw):
                self.assertIn(normalize_ua_phone(raw), (None, ''))


class ReviewFormHardeningTests(TestCase):
    def test_rejects_bad_phone_rating_and_honeypot(self):
        base = {
            'name': 'Олег',
            'text': 'Добре',
            'city_name': 'Київ',
            'consent': True,
            'rating': '5',
            'phone': '',
            'website': '',
        }
        bad_phone = ReviewForm(data={**base, 'phone': 'abc'})
        self.assertFalse(bad_phone.is_valid())
        self.assertIn('phone', bad_phone.errors)

        bad_rating = ReviewForm(data={**base, 'rating': '9'})
        self.assertFalse(bad_rating.is_valid())
        self.assertIn('rating', bad_rating.errors)

        spam = ReviewForm(data={**base, 'website': 'http://spam.example'})
        self.assertFalse(spam.is_valid())
        self.assertIn('website', spam.errors)

        ok = ReviewForm(data={**base, 'phone': '0991234567', 'rating': '4'})
        self.assertTrue(ok.is_valid(), ok.errors)
        self.assertEqual(ok.cleaned_data['phone'], '+380991234567')
        self.assertEqual(ok.cleaned_data['rating'], 4)


class ContactFormPhoneTests(TestCase):
    def test_requires_ua_phone(self):
        form = ContactMessageForm(data={
            'name': 'Анна',
            'phone': 'abc',
            'message': 'Питання',
            'consent': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        ok = ContactMessageForm(data={
            'name': 'Анна',
            'phone': '+380 99 111-22-33',
            'message': 'Питання',
            'consent': True,
        })
        self.assertTrue(ok.is_valid(), ok.errors)
        self.assertEqual(ok.cleaned_data['phone'], '+380991112233')


@override_settings(RATELIMIT_ENABLE=True)
class FormRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        City.objects.create(name='Київ', slug='kyiv-rl', phone='+380992222222')

    def test_review_contact_chat_limited_to_three(self):
        review_url = reverse('reviews:review_submit')
        contact_url = reverse('leads:contact_submit')
        chat_url = reverse('bot:chat_send')
        review_payload = {
            'name': 'Олег',
            'text': 'Добре',
            'city_name': 'Київ',
            'phone': '',
            'consent': True,
            'rating': '5',
            'website': '',
        }
        contact_payload = {
            'name': 'Анна',
            'phone': '+380991112233',
            'message': 'Питання',
            'consent': True,
        }
        client = Client()
        for _ in range(3):
            self.assertIn(
                client.post(review_url, review_payload).status_code,
                (200, 302),
            )
        blocked = client.post(review_url, review_payload)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(Review.objects.count(), 3)

        for _ in range(3):
            self.assertIn(
                client.post(contact_url, contact_payload).status_code,
                (200, 302),
            )
        self.assertEqual(client.post(contact_url, contact_payload).status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 3)

        client.get(reverse('bot:chat_log'))
        for _ in range(3):
            self.assertEqual(
                client.post(chat_url, {'text': 'привіт'}).status_code,
                200,
            )
        fourth = client.post(chat_url, {'text': 'ще'})
        self.assertEqual(fourth.status_code, 200)
        self.assertContains(fourth, 'Забагато запитів')


class ClientIpTests(SimpleTestCase):
    def test_spoofed_forwarded_for_counts_as_rightmost(self):
        request = RequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='9.9.9.9, 5.5.5.5',
            REMOTE_ADDR='127.0.0.1',
        )
        self.assertEqual(client_ip(request), '5.5.5.5')

    def test_blank_forwarded_for_falls_back_to_remote_addr(self):
        request = RequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR=' , ',
            REMOTE_ADDR='203.0.113.9',
        )
        self.assertEqual(client_ip(request), '203.0.113.9')


@override_settings(RATELIMIT_ENABLE=True)
class ForwardedForRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_changing_leftmost_forwarded_for_does_not_bypass_limit(self):
        factory = RequestFactory()
        original = factory.post('/', HTTP_X_FORWARDED_FOR='9.9.9.9, 5.5.5.5')
        self.assertEqual(client_ip(original), '5.5.5.5')
        for _ in range(3):
            self.assertTrue(allow_request(original, 'xff', limit=3, window=600))
        self.assertFalse(allow_request(original, 'xff', limit=3, window=600))

        rotated = factory.post('/', HTTP_X_FORWARDED_FOR='8.8.8.8, 5.5.5.5')
        self.assertEqual(client_ip(rotated), '5.5.5.5')
        self.assertFalse(allow_request(rotated, 'xff', limit=3, window=600))
