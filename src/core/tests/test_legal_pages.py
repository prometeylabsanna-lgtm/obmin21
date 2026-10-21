import os
import re

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.legal_copy import (
    COOKIE_BODY,
    LEGAL_PAGE_BODIES,
    OFFER_BODY,
    OFFER_SENTENCE_AFTER,
    OFFER_SENTENCE_BEFORE,
    PRIVACY_BODY,
    PRIVACY_SENTENCE_AFTER,
    PRIVACY_SENTENCE_BEFORE,
    apply_legal_replacements,
)
from src.content.models import CookiePage, OfferPage, PrivacyPage
from src.core.models import SiteSettings
from src.core.tests.test_services_page_mode import load_filter_stopwords

_ENV = 'EXCHANGE_ONLY_MODE'
_PAGES = (
    ('content:privacy', PrivacyPage, 'PrivacyPage', PRIVACY_BODY),
    ('content:offer', OfferPage, 'OfferPage', OFFER_BODY),
    ('content:cookies', CookiePage, 'CookiePage', COOKIE_BODY),
)


def _old_body(cleaned):
    text = cleaned
    text = text.replace(PRIVACY_SENTENCE_AFTER, PRIVACY_SENTENCE_BEFORE)
    text = text.replace(OFFER_SENTENCE_AFTER, OFFER_SENTENCE_BEFORE)
    return text


class LegalPageCopyTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = self._saved_env
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _load_old_pages(self):
        pages = []
        for _url_name, model, key, cleaned in _PAGES:
            page = model.load()
            page.body = _old_body(cleaned)
            page.seo_title = ''
            page.seo_description = ''
            page.save(update_fields=['body', 'seo_title', 'seo_description'])
            pages.append((key, page, cleaned))
        return pages

    def test_replacement_is_idempotent_and_keeps_editor_text(self):
        pages = self._load_old_pages()
        apply_legal_replacements(apps, None)
        for key, page, cleaned in pages:
            page.refresh_from_db()
            self.assertEqual(page.body, cleaned)
            self.assertEqual(page.body, LEGAL_PAGE_BODIES[key])
            self.assertNotIn(PRIVACY_SENTENCE_BEFORE, page.body)
            self.assertNotIn(OFFER_SENTENCE_BEFORE, page.body)
        snapshot = {
            key: model.objects.get(pk=1).body
            for _url_name, model, key, _cleaned in _PAGES
        }
        apply_legal_replacements(apps, None)
        for key, body in snapshot.items():
            model = dict((item[2], item[1]) for item in _PAGES)[key]
            self.assertEqual(model.objects.get(pk=1).body, body)

        privacy = PrivacyPage.objects.get(pk=1)
        privacy.body = 'Окремий абзац, який залишив редактор.'
        privacy.save(update_fields=['body'])
        apply_legal_replacements(apps, None)
        privacy.refresh_from_db()
        self.assertEqual(privacy.body, 'Окремий абзац, який залишив редактор.')

    def test_rendered_pages_have_no_stop_words_in_both_modes(self):
        _stop_words, matches_stop_words = load_filter_stopwords()
        self.assertTrue(matches_stop_words(PRIVACY_SENTENCE_BEFORE))
        self.assertTrue(matches_stop_words(OFFER_SENTENCE_BEFORE))
        self.assertFalse(matches_stop_words(PRIVACY_BODY))
        self.assertFalse(matches_stop_words(OFFER_BODY))
        self.assertFalse(matches_stop_words(COOKIE_BODY))
        self._load_old_pages()
        apply_legal_replacements(apps, None)

        for enabled in (False, True):
            self._mode(enabled)
            for url_name, _model, _key, cleaned in _PAGES:
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                article = re.search(
                    r'<article class="legal-page"[\s\S]*?</article>',
                    html,
                )
                self.assertIsNotNone(article)
                region = article.group(0)
                description = re.search(
                    r'<meta name="description" content="([^"]*)"',
                    html,
                )
                if description:
                    region = region + '\n' + description.group(1)
                self.assertFalse(matches_stop_words(region))
                self.assertIn(cleaned.split('\n\n', 1)[0][:40], html)
                self.assertNotIn('криптовалют', region.casefold())
                self.assertNotIn('переказ', region.casefold())

    def test_seed_and_migration_use_cleaned_copy(self):
        root = __import__('pathlib').Path(__file__).resolve().parents[3]
        seed = (root / 'src/core/management/commands/seed_demo.py').read_text(
            encoding='utf-8',
        )
        self.assertIn('privacy.body = PRIVACY_BODY', seed)
        self.assertIn('offer.body = OFFER_BODY', seed)
        self.assertIn('cookies.body = COOKIE_BODY', seed)
        self.assertNotIn(PRIVACY_SENTENCE_BEFORE, seed)
        self.assertNotIn(OFFER_SENTENCE_BEFORE, seed)
        migration = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in (root / 'src/content/migrations').glob('0023_*.py')
        )
        self.assertIn('apply_legal_replacements', migration)
        self.assertIn('noop_reverse', migration)
