import os
from contextlib import contextmanager
from types import SimpleNamespace

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.test import RequestFactory, TestCase

from src.blog.models import Category, Post
from src.content.models import (
    AdvantagesPage,
    BlogPage,
    ContactsPage,
    CookiePage,
    FaqPage,
    OfferPage,
    PrivacyPage,
    RatesPage,
    Service,
    ServicesPage,
)
from src.content.service_blocks import SERVICE_BLOCKS
from src.core.exchange_mode import (
    NEUTRAL_DESCRIPTION,
    is_exchange_only,
    mode_meta,
)
from src.core.exchange_stopwords import matches_stop_words
from src.core.models import SiteSettings
from src.rates.models import CurrencyPair

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_SEO = 'ZZ-SEO-ORIG'
_SEO_MODE = 'ZZ-SEO-MODE'
_TITLE = 'ZZ-TITLE-ORIG'
_TITLE_MODE = 'ZZ-TITLE-MODE'

_PAGES = (
    ('services', '/posluhy/', ServicesPage, 'hero_text', 160, True),
    ('advantages', '/perevahy/', AdvantagesPage, 'hero_lead', 160, True),
    ('contacts', '/kontakty/', ContactsPage, 'heading', None, True),
    ('faq', '/faq/', FaqPage, 'lead', None, True),
    ('blog', '/blog/', BlogPage, 'intro', 160, True),
    ('rates', '/kursy/', RatesPage, 'intro', 160, True),
)

_LEGAL = (
    (PrivacyPage, '/polityka-konfidentsiynosti/'),
    (OfferPage, '/publichna-oferta/'),
    (CookiePage, '/polityka-cookie/'),
)

_MODE_COLUMNS = {
    ServicesPage: (
        'seo_description_mode', 'seo_title_mode', 'intro_mode', 'title_mode', 'hero_text_mode',
    ),
    Service: ('short_desc_mode', 'block_text_mode', 'block_points_mode', 'block_cta_mode'),
    AdvantagesPage: (
        'seo_description_mode', 'seo_title_mode', 'title_mode', 'hero_lead_mode',
    ),
    ContactsPage: (
        'seo_title_mode', 'title_mode', 'seo_description_mode', 'heading_mode',
    ),
    FaqPage: ('seo_description_mode', 'seo_title_mode', 'title_mode', 'lead_mode'),
    BlogPage: ('seo_description_mode', 'seo_title_mode', 'title_mode', 'intro_mode'),
    Post: ('seo_title_mode', 'title_mode', 'seo_description_mode', 'excerpt_mode'),
    RatesPage: ('seo_description_mode', 'seo_title_mode', 'title_mode', 'intro_mode'),
    CurrencyPair: ('seo_title_mode', 'seo_description_mode', 'intro_mode'),
}


def _pad(prefix, size=180):
    return prefix + ('X' * (size - len(prefix)))


@contextmanager
def _attrs(model, **attrs):
    for name in attrs:
        try:
            model._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        raise AssertionError(f'{model.__name__}.{name} is a real column')
    for name, value in attrs.items():
        setattr(model, name, value)
    try:
        yield
    finally:
        for name in attrs:
            delattr(model, name)


class ModeMetaTests(TestCase):
    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def _meta(self, response):
        html = response.content.decode()
        marker = '<meta name="description" content="'
        start = html.find(marker)
        self.assertNotEqual(start, -1)
        start += len(marker)
        end = html.find('"', start)
        self.assertGreater(end, start)
        return html[start:end]

    def _expect(self, url, description, title, banned):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertEqual(response.context['page_description'], description, url)
        self.assertEqual(response.context['page_title'], title, url)
        meta = self._meta(response)
        self.assertEqual(meta, description, url)
        for token in banned:
            self.assertNotIn(token, response.context['page_description'], url)
            self.assertNotIn(token, meta, url)
        return response

    def test_neutral_phrase_avoids_stop_words(self):
        self.assertTrue(NEUTRAL_DESCRIPTION.strip())
        self.assertLessEqual(len(NEUTRAL_DESCRIPTION), 160)
        self.assertFalse(matches_stop_words(NEUTRAL_DESCRIPTION))

    def test_fallback_columns(self):
        for model, names in _MODE_COLUMNS.items():
            for name in names:
                model._meta.get_field(name)

    def test_mode_meta_helper(self):
        hero = _pad('H-')
        lead = _pad('L-')
        seo = _pad('S-', 200)
        hero_mode = _pad('HM-')
        obj = SimpleNamespace(
            seo_description=seo,
            hero=hero,
            lead=lead,
            title='TITLE',
            seo_title='',
            seo_description_mode='  MODE  ',
            hero_mode=hero_mode,
            lead_mode='   ',
            title_mode='',
            seo_title_mode='',
        )
        outside = dict(limit=None, outside_default='CHF — курс обміну')
        self._mode(False)
        self.assertEqual(mode_meta(obj, 'seo_description', 'hero'), seo)
        self.assertGreater(len(seo), 160)
        obj.seo_description = ''
        self.assertEqual(mode_meta(obj, 'seo_description', 'hero'), hero[:160])
        self.assertEqual(mode_meta(obj, 'seo_description', 'lead', 'title', limit=None), lead)
        obj.lead = ''
        self.assertEqual(mode_meta(obj, 'seo_description', 'lead', 'title', limit=None), 'TITLE')
        self.assertEqual(mode_meta(obj, 'seo_title', **outside), 'CHF — курс обміну')
        obj.seo_title = '   '
        self.assertEqual(mode_meta(obj, 'seo_title', **outside), '   ')
        spaced = SimpleNamespace(seo_description='   ', hero='HERO')
        self.assertEqual(mode_meta(spaced, 'seo_description', 'hero'), '   ')
        self._mode(True)
        obj.seo_description = 'ORIG'
        self.assertEqual(mode_meta(obj, 'seo_description', 'hero'), 'MODE')
        obj.seo_description_mode = ' \n '
        self.assertEqual(mode_meta(obj, 'seo_description', 'hero'), hero_mode[:160])
        obj.hero_mode = '  '
        self.assertEqual(mode_meta(obj, 'seo_description', 'hero'), NEUTRAL_DESCRIPTION)
        bare = SimpleNamespace(seo_description='ORIG', hero='HERO-ORIG')
        self.assertEqual(mode_meta(bare, 'seo_description', 'hero'), NEUTRAL_DESCRIPTION)
        self.assertNotIn('ORIG', mode_meta(bare, 'seo_description', 'hero'))
        obj.seo_title = 'SEO-TITLE'
        self.assertEqual(mode_meta(obj, 'seo_title', **outside), NEUTRAL_DESCRIPTION)

    def test_mode_meta_uses_request_cache(self):
        self._mode(False)
        request = RequestFactory().get('/')
        self.assertFalse(is_exchange_only(request))
        self._mode(True)
        obj = SimpleNamespace(seo_description='ORIG', seo_description_mode='MODE')
        self.assertEqual(mode_meta(obj, 'seo_description', request=request), 'ORIG')
        self.assertEqual(mode_meta(obj, 'seo_description'), 'MODE')

    def _clear_text_modes(self, page):
        for field in page._meta.fields:
            if not field.name.endswith('_mode'):
                continue
            if field.get_internal_type() not in ('CharField', 'TextField'):
                continue
            setattr(page, field.name, '')

    def _run_page(self, url, model, fallback_name, limit, has_modes):
        page = model.load()
        self._clear_text_modes(page)
        fallback = _pad('ZZF-')
        page.seo_description = _SEO
        page.seo_title = ''
        page.title = _TITLE
        setattr(page, fallback_name, fallback)
        if has_modes:
            page.seo_description_mode = _SEO_MODE
            page.seo_title_mode = _TITLE_MODE
        page.save()

        outside_ban = [_SEO_MODE, _TITLE_MODE, 'ZZF-']
        mode_ban = [_SEO, 'ZZF-', _TITLE]
        self._mode(False)
        self._expect(url, _SEO, _TITLE, outside_ban)

        self._mode(True)
        if has_modes:
            self._expect(url, _SEO_MODE, _TITLE_MODE, mode_ban)
            page.seo_description_mode = ''
            page.seo_title_mode = ''
            page.save(update_fields=['seo_description_mode', 'seo_title_mode'])
        else:
            self._expect(url, NEUTRAL_DESCRIPTION, NEUTRAL_DESCRIPTION, mode_ban)
            with _attrs(model, seo_description_mode=_SEO_MODE, seo_title_mode=_TITLE_MODE):
                self._expect(url, _SEO_MODE, _TITLE_MODE, mode_ban)
                self._mode(False)
                self._expect(url, _SEO, _TITLE, outside_ban)
            self._mode(True)

        self._expect(url, NEUTRAL_DESCRIPTION, NEUTRAL_DESCRIPTION, mode_ban)
        page.seo_description = ''
        page.save(update_fields=['seo_description'])
        expected = fallback if limit is None else fallback[:160]
        self._mode(False)
        self._expect(url, expected, _TITLE, [_SEO_MODE])
        if limit is None:
            self.assertEqual(expected, fallback)
            self.assertGreater(len(expected), 160)
        else:
            self.assertEqual(len(expected), 160)
            self.assertNotEqual(expected, fallback)
        self._mode(True)
        self._expect(url, NEUTRAL_DESCRIPTION, NEUTRAL_DESCRIPTION, ['ZZF-', _TITLE])

    def test_singleton_pages(self):
        for label, url, model, field, limit, has_modes in _PAGES:
            with self.subTest(page=label):
                self._run_page(url, model, field, limit, has_modes)

    def test_services_ignore_intro_mode_and_block_text(self):
        page = ServicesPage.load()
        page.seo_description = ''
        page.seo_description_mode = ''
        page.intro = 'ZZ-INTRO-ORIG'
        page.intro_mode = 'ZZ-INTRO-MODE'
        page.hero_text = 'ZZ-HERO-ORIG'
        page.seo_title = 'ZZ-TITLE-SEO'
        page.seo_title_mode = ''
        page.save()
        plain = Service.objects.create(
            title='Каса',
            slug='meta-plain',
            short_desc='ZZ-SHORT-ORIG',
            sort_order=0,
            exchange_safe=True,
        )
        Service.objects.create(
            title='Монети',
            slug='kryptovalyuta',
            short_desc='ZZ-SHORT-CRYPTO',
            sort_order=1,
            exchange_safe=True,
        )
        block = SERVICE_BLOCKS['kryptovalyuta']['text']
        self._mode(False)
        response = self._expect('/posluhy/', 'ZZ-HERO-ORIG', 'ZZ-TITLE-SEO', ['ZZ-INTRO-MODE'])
        blocks = {item.slug: item.block_text for item in response.context['services']}
        self.assertEqual(blocks['meta-plain'], plain.short_desc)
        self.assertEqual(blocks['kryptovalyuta'], block)
        self.assertContains(response, 'Підтвердження транзакції')

        self._mode(True)
        response = self._expect(
            '/posluhy/',
            NEUTRAL_DESCRIPTION,
            NEUTRAL_DESCRIPTION,
            ['ZZ-HERO-ORIG', 'ZZ-INTRO-MODE', 'ZZ-INTRO-ORIG', 'ZZ-TITLE-SEO'],
        )
        blocks = {item.slug: item.block_text for item in response.context['services']}
        self.assertEqual(blocks['meta-plain'], NEUTRAL_DESCRIPTION)
        self.assertEqual(blocks['kryptovalyuta'], NEUTRAL_DESCRIPTION)
        self.assertNotContains(response, 'ZZ-SHORT-ORIG')
        self.assertNotContains(response, 'Підтвердження транзакції')

        Service.objects.update(short_desc_mode='ZZ-SHORT-MODE')
        self._mode(False)
        response = self.client.get('/posluhy/')
        blocks = {item.slug: item.block_text for item in response.context['services']}
        self.assertEqual(blocks['kryptovalyuta'], block)
        self._mode(True)
        response = self.client.get('/posluhy/')
        blocks = {item.slug: item.block_text for item in response.context['services']}
        self.assertEqual(blocks['meta-plain'], 'ZZ-SHORT-MODE')
        self.assertEqual(blocks['kryptovalyuta'], 'ZZ-SHORT-MODE')
        self.assertNotIn('ZZ-SHORT-ORIG', blocks['meta-plain'])
        self.assertNotIn(block, blocks['kryptovalyuta'])

    def test_advantages_hero_mode_is_sliced(self):
        page = AdvantagesPage.load()
        self._clear_text_modes(page)
        page.seo_description = _SEO
        page.hero_lead = _pad('ZZ-HERO-ORIG-')
        page.seo_title = ''
        page.title = _TITLE
        hero_mode = _pad('ZZ-HERO-MODE-')
        page.hero_lead_mode = hero_mode
        page.save()
        self._mode(True)
        self._expect(
            '/perevahy/',
            hero_mode[:160],
            NEUTRAL_DESCRIPTION,
            [_SEO, 'ZZ-HERO-ORIG'],
        )
        self.assertNotContains(self.client.get('/perevahy/'), 'ZZ-HERO-ORIG')
        self._mode(False)
        self._expect('/perevahy/', _SEO, _TITLE, ['ZZ-HERO-MODE'])

    def test_faq_uses_title_only_as_last_fallback(self):
        page = FaqPage.load()
        page.seo_description = ''
        page.seo_description_mode = ''
        page.lead = ''
        page.title = 'ZZ-FAQ-TITLE'
        page.seo_title = ''
        page.seo_title_mode = ''
        page.save()
        self._mode(False)
        self._expect('/faq/', 'ZZ-FAQ-TITLE', 'ZZ-FAQ-TITLE', [])
        self._mode(True)
        self._expect('/faq/', NEUTRAL_DESCRIPTION, NEUTRAL_DESCRIPTION, ['ZZ-FAQ-TITLE'])

    def test_legal_pages(self):
        paragraph = _pad('ZZ-LEGAL-')
        body = paragraph + '\n\nZZ-LEGAL-REST'
        for model, url in _LEGAL:
            with self.subTest(url=url):
                page = model.load()
                page.seo_description = _SEO
                page.seo_title = ''
                page.title = 'ZZ-LEGAL-TITLE'
                page.body = body
                page.save()
                self._mode(False)
                self._expect(url, _SEO, 'ZZ-LEGAL-TITLE', ['ZZ-LEGAL-REST'])
                page.seo_description = ''
                page.save(update_fields=['seo_description'])
                self._expect(url, paragraph[:160], 'ZZ-LEGAL-TITLE', ['ZZ-LEGAL-REST'])
                self._mode(True)
                response = self._expect(
                    url,
                    NEUTRAL_DESCRIPTION,
                    NEUTRAL_DESCRIPTION,
                    ['ZZ-LEGAL-', 'ZZ-LEGAL-TITLE', 'ZZ-LEGAL-REST'],
                )
                self.assertContains(response, 'ZZ-LEGAL-')
                with _attrs(
                    model,
                    seo_description_mode=_SEO_MODE,
                    seo_title_mode=_TITLE_MODE,
                ):
                    self._expect(url, _SEO_MODE, _TITLE_MODE, ['ZZ-LEGAL-'])
                    self._mode(False)
                    self._expect(url, paragraph[:160], 'ZZ-LEGAL-TITLE', [_SEO_MODE])

    def test_legal_body_mode_is_sliced(self):
        original = _pad('ZZ-BODY-ORIG-')
        mode_body = _pad('ZZ-BODY-MODE-')
        page = PrivacyPage.load()
        page.seo_description = ''
        page.seo_title = ''
        page.title = 'ZZ-LEGAL-TITLE'
        page.body = original + '\n\nrest'
        page.save()
        with _attrs(PrivacyPage, body_mode=mode_body + '\n\nignored'):
            self._mode(True)
            self._expect(
                '/polityka-konfidentsiynosti/',
                mode_body[:160],
                NEUTRAL_DESCRIPTION,
                ['ZZ-BODY-ORIG'],
            )
            self._mode(False)
            self._expect(
                '/polityka-konfidentsiynosti/',
                original[:160],
                'ZZ-LEGAL-TITLE',
                ['ZZ-BODY-MODE'],
            )

    def test_blog_category_keeps_its_name(self):
        page = BlogPage.load()
        page.seo_description = _SEO
        page.seo_description_mode = ''
        page.intro = 'ZZ-BLOG-INTRO'
        page.seo_title = ''
        page.seo_title_mode = ''
        page.title = _TITLE
        page.save()
        category = Category.objects.create(name='ZZ-CAT', slug='zz-cat')
        Post.objects.create(
            category=category,
            title='ZZ-POST',
            slug='zz-cat-post',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        url = '/blog/kategoriya/zz-cat/'
        description = 'Статті рубрики ZZ-CAT.'
        self._mode(False)
        self._expect(url, description, 'ZZ-CAT', ['ZZ-BLOG-INTRO', _TITLE, _SEO])
        self._mode(True)
        self._expect(url, description, 'ZZ-CAT', [_SEO, 'ZZ-BLOG-INTRO', _TITLE])

    def test_post_detail(self):
        category = Category.objects.create(name='Нотатки', slug='notatky')
        excerpt = _pad('ZZ-EXCERPT-')
        post = Post.objects.create(
            category=category,
            title='ZZ-POST-TITLE',
            slug='zz-meta-post',
            excerpt=excerpt,
            body='Текст',
            seo_description=_SEO,
            seo_title='',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        url = '/blog/zz-meta-post/'
        self._mode(False)
        self._expect(url, _SEO, 'ZZ-POST-TITLE', ['ZZ-EXCERPT-'])
        post.seo_description = ''
        post.save(update_fields=['seo_description'])
        self._expect(url, excerpt[:160], 'ZZ-POST-TITLE', [])
        self._mode(True)
        self._expect(
            url,
            NEUTRAL_DESCRIPTION,
            NEUTRAL_DESCRIPTION,
            ['ZZ-EXCERPT-', _SEO, 'ZZ-POST-TITLE'],
        )
        post.seo_description_mode = _SEO_MODE
        post.seo_title_mode = _TITLE_MODE
        post.save(update_fields=['seo_description_mode', 'seo_title_mode'])
        self._expect(url, _SEO_MODE, _TITLE_MODE, ['ZZ-EXCERPT-', 'ZZ-POST-TITLE'])
        self._mode(False)
        self._expect(url, excerpt[:160], 'ZZ-POST-TITLE', [_SEO_MODE, _TITLE_MODE])

    def test_pair_detail(self):
        intro = _pad('ZZ-PAIR-')
        pair = CurrencyPair.objects.create(
            code='CHF',
            name='Франк',
            slug='chf-meta',
            intro=intro,
            seo_description=_SEO,
            seo_title='',
            exchange_safe=True,
        )
        url = f'/{pair.slug}/'
        outside_title = f'{pair.code} — курс обміну'
        self._mode(False)
        self._expect(url, _SEO, outside_title, ['ZZ-PAIR-'])
        pair.seo_description = ''
        pair.save(update_fields=['seo_description'])
        self._expect(url, intro[:160], outside_title, [])
        self._mode(True)
        self._expect(
            url,
            NEUTRAL_DESCRIPTION,
            NEUTRAL_DESCRIPTION,
            ['ZZ-PAIR-', _SEO, 'CHF'],
        )
        pair.seo_description_mode = _SEO_MODE
        pair.seo_title_mode = _TITLE_MODE
        pair.save(update_fields=['seo_description_mode', 'seo_title_mode'])
        self._expect(url, _SEO_MODE, _TITLE_MODE, ['ZZ-PAIR-', 'CHF'])
        self._mode(False)
        self._expect(url, intro[:160], outside_title, [_SEO_MODE, _TITLE_MODE])
