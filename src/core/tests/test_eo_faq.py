import importlib
import os

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.faq_defaults import BASE_FAQ
from src.content.models import FaqItem, HomePage
from src.core.exchange_stopwords import matches_stop_words
from src.core.models import SiteSettings

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_EMPTY = 'Питання зʼявляться незабаром'


class ExchangeFaqTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _pages(self):
        return (
            reverse('content:faq'),
            reverse('core:home'),
        )

    def test_fallback_shows_base_questions_when_none_are_safe(self):
        FaqItem.objects.update(exchange_safe=False)
        self._mode(True)
        for url in self._pages():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            items = list(response.context['faq_items'])
            self.assertEqual(
                [(item.question, item.answer) for item in items],
                list(BASE_FAQ),
            )
            self.assertTrue(all(item.exchange_safe for item in items))
            self.assertTrue(all(getattr(item, 'pk', None) is None for item in items))
            self.assertNotContains(response, _EMPTY)
            for question, answer in BASE_FAQ:
                self.assertContains(response, question)
                self.assertContains(response, answer)

    def test_fallback_is_absent_outside_exchange_only(self):
        FaqItem.objects.update(is_active=False)
        self._mode(False)
        response = self.client.get(reverse('content:faq'))
        self.assertEqual(list(response.context['faq_items']), [])
        self.assertContains(response, _EMPTY)

    def test_seeded_items_visible_on_faq_and_home(self):
        hidden = FaqItem.objects.create(
            question='Як надіслати переказ SWIFT?',
            answer='Прихована відповідь',
            exchange_safe=False,
            is_active=True,
            sort_order=1,
        )
        page = HomePage.objects.filter(pk=1).first()
        for offset, (question, answer) in enumerate(BASE_FAQ):
            item = FaqItem.objects.get(question=question)
            self.assertEqual(item.answer, answer)
            self.assertTrue(item.is_active)
            self.assertTrue(item.exchange_safe)
            self.assertEqual(item.sort_order, 900 + offset)
            self.assertEqual(item.home_page_id, page.pk if page else None)
        self._mode(True)
        for url in self._pages():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            questions = [item.question for item in response.context['faq_items']]
            for question, answer in BASE_FAQ:
                self.assertIn(question, questions)
                self.assertContains(response, question)
                self.assertContains(response, answer)
            self.assertNotIn(hidden.question, questions)
            self.assertNotContains(response, hidden.question)
            self.assertNotContains(response, _EMPTY)

    def test_seed_updates_same_question_and_leaves_other_rows(self):
        other = FaqItem.objects.create(
            question='Стороннє питання',
            answer='Стара відповідь',
            exchange_safe=False,
            is_active=True,
            sort_order=3,
        )
        count = FaqItem.objects.count()
        migration = importlib.import_module(
            'src.content.migrations.0030_seed_exchange_safe_faq',
        )
        migration.seed_exchange_faq(apps, None)
        migration.seed_exchange_faq(apps, None)
        self.assertEqual(FaqItem.objects.count(), count)
        self.assertEqual(
            FaqItem.objects.filter(question=BASE_FAQ[0][0]).count(),
            1,
        )
        other.refresh_from_db()
        self.assertEqual(other.answer, 'Стара відповідь')
        self.assertFalse(other.exchange_safe)
        self.assertEqual(other.sort_order, 3)
        self.assertTrue(other.is_active)

    def test_default_faq_texts_do_not_match_stop_words(self):
        texts = [text for pair in BASE_FAQ for text in pair]
        self.assertEqual(len(texts), 10)
        for text in texts:
            self.assertFalse(matches_stop_words(text), text)
