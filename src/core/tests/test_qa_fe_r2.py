"""QA FE r2 (tester round 2): data-qa лід-форми, admin search override, розміри обкладинок."""

import re
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.core.models import SiteSettings

_FORM_TAGS = re.compile(r'<form\b[^>]*>', re.I)


class LeadFormMarkerTests(TestCase):
    def setUp(self):
        cache.clear()
        SiteSettings.load()

    def _forms(self, html):
        return _FORM_TAGS.findall(html)

    def test_lead_form_is_chat_form_on_normal_get(self):
        html = self.client.get(reverse('content:privacy')).content.decode()
        lead = [f for f in self._forms(html) if 'data-qa="lead-form"' in f]
        self.assertEqual(len(lead), 1)
        self.assertIn(reverse('bot:chat_send'), lead[0])
        callback = [f for f in self._forms(html) if 'data-qa="lead-form-callback"' in f]
        self.assertEqual(len(callback), 1)
        self.assertIn(reverse('bot:chat_callback'), callback[0])

    def test_lead_success_not_on_normal_get(self):
        html = self.client.get(reverse('content:privacy')).content.decode()
        self.assertNotIn('data-qa="lead-success"', html)

    def test_contact_modal_has_no_lead_form(self):
        html = self.client.get(reverse('leads:contact_modal')).content.decode()
        self.assertNotIn('data-qa="lead-form"', html)
        self.assertNotIn('<form', html.lower())


class AdminSearchOverrideTests(TestCase):
    def test_override_does_not_use_removed_alpine_component(self):
        path = Path(settings.BASE_DIR) / 'templates' / 'unfold' / 'helpers' / 'search.html'
        source = path.read_text(encoding='utf-8')
        body = re.sub(r'{% comment %}.*?{% endcomment %}', '', source, flags=re.S)
        self.assertNotIn('searchDropdown', body)
        self.assertNotIn('openSearchResults', body)
        self.assertIn("$dispatch('opencommand')", body)


class CoverSizeTests(TestCase):
    """Обкладинки lazy, але з width/height або фіксованою висотою контейнера (без CLS)."""

    _TEMPLATES = (
        'core/home.html',
        'content/services_list.html',
        'partials/blog_list.html',
        'blog/post_detail.html',
    )
    _CSS = {
        'home.css': ('.article-slide__media {',),
        'blog.css': ('.blog-card__media {',),
        'article.css': ('.article-related__media {', '.article-fig img {'),
    }

    def test_lazy_cover_imgs_carry_size_attrs(self):
        root = Path(settings.BASE_DIR) / 'templates'
        for name in self._TEMPLATES:
            src = (root / name).read_text(encoding='utf-8')
            for tag in re.findall(r'<img\b[^>]*loading="lazy"[^>]*>', src):
                if 'image_url' in tag or 'fig_url' in tag:
                    self.assertIn('width=', tag, name)
                    self.assertIn('height=', tag, name)

    def test_media_boxes_reserve_height(self):
        css_dir = Path(settings.BASE_DIR) / 'src' / 'core' / 'static' / 'css' / 'components'
        for fname, selectors in self._CSS.items():
            css = (css_dir / fname).read_text(encoding='utf-8')
            for sel in selectors:
                start = css.index(sel)
                block = css[start:css.index('}', start)]
                self.assertRegex(block, r'\n\s*(height|aspect-ratio):', sel)


class ChatLeadSuccessMarkerTests(TestCase):
    """CP4: data-qa="lead-success" рівно 1 раз — лише у свіжій відповіді, де створено заявку."""

    MARK = 'data-qa="lead-success"'

    def setUp(self):
        from src.core.tests.test_qa_2026_11_03 import _fixtures

        cache.clear()
        SiteSettings.load()
        self.city, self.branch, self.pair = _fixtures('cp4')

    def _confirm(self, user, data):
        from src.bot.outbox import Outgoing
        from src.bot.services import submit_exchange, upsert_profile

        profile = upsert_profile(user)
        obj = submit_exchange(profile.chat_id, profile, {
            'city_id': self.city.pk, 'pair_id': self.pair.pk, 'direction': 'sell',
            'amount_give': '100', 'branch_id': self.branch.pk,
            'name': 'Іван Тест', 'phone': '+380991112233',
        })
        return [Outgoing(html=f'Курс зафіксовано до {obj.expires_at}.'), Outgoing(html='Меню')]

    def _post_confirm(self):
        from unittest.mock import patch

        with patch('src.leads.services.notify_new_lead'), \
                patch('src.bot.web_views.handle_callback', side_effect=self._confirm):
            return self.client.post(reverse('bot:chat_callback'), {'data': 'ex:confirm', 'label': 'Так'})

    def test_success_has_exactly_one_marker(self):
        from src.leads.models import ExchangeRequest

        html = self._post_confirm().content.decode()
        self.assertEqual(html.count(self.MARK), 1)
        lead = ExchangeRequest.objects.get()
        self.assertIn(f'data-lead-id="{lead.pk}"', html)
        marked = re.search(r'<article[^>]*lead-success[^>]*>(.*?)</article>', html, re.S).group(1)
        self.assertIn('Курс зафіксовано', marked)

    def test_intermediate_step_has_no_marker(self):
        html = self.client.post(reverse('bot:chat_send'), {'text': 'курси'}).content.decode()
        self.assertEqual(html.count(self.MARK), 0)

    def test_error_has_no_marker(self):
        from unittest.mock import patch

        with patch('src.bot.web_views.handle_callback', side_effect=ValueError('boom')):
            html = self.client.post(reverse('bot:chat_callback'), {'data': 'ex:confirm'}).content.decode()
        self.assertIn('Сталася помилка', html)
        self.assertEqual(html.count(self.MARK), 0)

    def test_history_and_next_step_do_not_repeat_marker(self):
        self._post_confirm()
        history = self.client.get(reverse('bot:chat_log')).content.decode()
        self.assertIn('Курс зафіксовано', history)
        self.assertEqual(history.count(self.MARK), 0)
        nxt = self.client.post(reverse('bot:chat_send'), {'text': 'курси'}).content.decode()
        self.assertEqual(nxt.count(self.MARK), 0)
