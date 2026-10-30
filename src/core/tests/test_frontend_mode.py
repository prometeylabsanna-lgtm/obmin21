import inspect
import json
import os
from contextlib import contextmanager

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from src.blog.models import Category, Post
from src.content.models import CitiesPage, HomePage, HomeStat, ReviewsPage, Service
from src.core.exchange_mode import NEUTRAL_DESCRIPTION
from src.core.models import SiteSettings
from src.network.models import City

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_TRIGGER_KEYS = {
    'slug',
    'name',
    'nameIn',
    'bannerUrl',
    'bannerTitle',
    'bannerSuffix',
    'bannerText',
    'bannerHidden',
    'branchId',
}
_ART_KEYS = {'post', 'art', 'related', 'page_title', 'page_description', 'breadcrumb_items'}
_LAYOUT = {
    'h1a': 'FE-H1A',
    'h1b': 'FE-H1B',
    'lead': 'FE-LEAD',
    'read': 'FE-READ',
    'sections': [{
        'h': 'FE-SEC',
        'p': ['FE-P'],
        'list': ['FE-LI'],
        'fig': True,
    }],
    'fig_cap': 'FE-CAP',
    'fig_url': '/static/fe.jpg',
    'plain': False,
}


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


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


class FrontendModeTests(TestCase):
    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)
        self.city = City.objects.create(
            name='FE-CITY',
            slug='fe-city',
            phone='+380441112233',
            seo_title='FE-CITY-SEO',
            seo_description='FE-CITY-SEOD',
            banner_title='FE-BANNER-TITLE',
            banner_text='FE-BANNER-TEXT',
            banner_suffix='FE-BANNER-SUFFIX',
            seo_title_mode='',
            seo_description_mode='',
            banner_title_mode='',
            banner_text_mode='',
        )

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def _trigger(self):
        response = self.client.post(
            reverse('network:set_city'),
            {'city': self.city.slug},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response['HX-Trigger'])
        self.assertEqual(set(payload), {'cityChanged'})
        detail = payload['cityChanged']
        self.assertEqual(set(detail), _TRIGGER_KEYS)
        return detail

    def test_home_uses_visible_not_keyword_parser(self):
        source = inspect.getsource(
            __import__('src.core.views', fromlist=['HomeView']).HomeView.get_context_data
        )
        self.assertIn('.visible()', source)
        self.assertNotIn('matches_stop_words', source)
        self.assertNotIn('visible_queryset', source)
        self.assertNotIn('STOP_WORDS', source)
        Service.objects.create(
            title='крипто FE-HOME-SAFE',
            slug='fe-home-safe',
            short_desc='каса',
            exchange_safe=True,
            show_on_home=True,
        )
        Service.objects.create(
            title='FE-HOME-HIDDEN',
            slug='fe-home-hidden',
            short_desc='каса',
            exchange_safe=False,
            show_on_home=True,
        )
        self._mode(True)
        home = self.client.get(reverse('core:home'))
        titles = [item.title for item in home.context['services']]
        self.assertIn('крипто FE-HOME-SAFE', titles)
        self.assertNotIn('FE-HOME-HIDDEN', titles)
        self._mode(False)
        titles = [
            item.title
            for item in self.client.get(reverse('core:home')).context['services']
        ]
        self.assertIn('крипто FE-HOME-SAFE', titles)
        self.assertIn('FE-HOME-HIDDEN', titles)

    def test_home_stats_hide_empty_mode_text(self):
        page = HomePage.load()
        HomeStat.objects.all().delete()
        HomeStat.objects.create(
            page=page,
            number='FE-STAT-NUM',
            text='FE-STAT-TEXT',
            exchange_safe=True,
            is_active=True,
            sort_order=1,
        )
        HomeStat.objects.create(
            page=page,
            number='FE-STAT-HIDDEN-NUM',
            text='FE-STAT-HIDDEN',
            exchange_safe=False,
            is_active=True,
            sort_order=2,
        )
        HomeStat.objects.create(
            page=page,
            number='FE-STAT-OFF',
            text='FE-STAT-OFF',
            exchange_safe=True,
            is_active=False,
            sort_order=3,
        )

        def cards():
            return self.client.get(reverse('core:home')).context['home_stats']

        self._mode(False)
        self.assertEqual(
            [(item['title'], item['text']) for item in cards()],
            [('FE-STAT-NUM', 'FE-STAT-TEXT'), ('FE-STAT-HIDDEN-NUM', 'FE-STAT-HIDDEN')],
        )

        self._mode(True)
        home = self.client.get(reverse('core:home'))
        self.assertEqual(home.context['home_stats'], [])
        self.assertNotContains(home, 'FE-STAT-TEXT')
        self.assertNotContains(home, 'FE-STAT-NUM')
        self.assertNotContains(home, 'FE-STAT-HIDDEN')

        stat = HomeStat.objects.get(number='FE-STAT-NUM')
        stat.number_mode = 'FE-STAT-MODE-NUM'
        stat.text_mode = '   '
        stat.save(update_fields=['number_mode', 'text_mode'])
        self.assertEqual(cards(), [])
        self.assertNotContains(self.client.get(reverse('core:home')), 'FE-STAT-MODE-NUM')
        self.assertNotContains(self.client.get(reverse('core:home')), 'FE-STAT-TEXT')

        stat.text_mode = '  FE-STAT-MODE  '
        stat.number_mode = '  '
        stat.save(update_fields=['number_mode', 'text_mode'])
        self.assertEqual(cards(), [{'text': 'FE-STAT-MODE'}])

        stat.text_mode = ' FE-STAT-MODE '
        stat.number_mode = ' FE-NUM '
        stat.save(update_fields=['number_mode', 'text_mode'])
        self.assertEqual(cards(), [{'text': 'FE-STAT-MODE', 'title': 'FE-NUM'}])
        home = self.client.get(reverse('core:home'))
        self.assertContains(home, 'FE-STAT-MODE')
        self.assertContains(home, 'FE-NUM')
        self.assertNotContains(home, 'FE-STAT-TEXT')
        self._mode(False)
        self.assertEqual(
            [(item['title'], item['text']) for item in cards()],
            [('FE-STAT-NUM', 'FE-STAT-TEXT'), ('FE-STAT-HIDDEN-NUM', 'FE-STAT-HIDDEN')],
        )

    def test_set_city_banner_payload(self):
        self._mode(False)
        outside = self._trigger()
        self.assertEqual(outside['bannerTitle'], 'FE-BANNER-TITLE')
        self.assertEqual(outside['bannerText'], 'FE-BANNER-TEXT')
        self.assertIs(outside['bannerHidden'], False)
        self.assertEqual(outside['name'], 'FE-CITY')
        self.assertEqual(outside['bannerSuffix'], 'FE-BANNER-SUFFIX')

        self.city.banner_title_mode = '   '
        self.city.banner_text_mode = '\n'
        self.city.save(update_fields=['banner_title_mode', 'banner_text_mode'])
        self._mode(True)
        empty = self._trigger()
        self.assertEqual(empty['bannerTitle'], '')
        self.assertEqual(empty['bannerText'], '')
        self.assertIs(empty['bannerHidden'], True)
        self.assertNotIn('FE-BANNER-TITLE', empty['bannerTitle'])
        self.assertNotIn('FE-BANNER-TEXT', empty['bannerText'])

        self.city.banner_title_mode = ''
        self.city.banner_text_mode = '  FE-BANNER-MODE  '
        self.city.save(update_fields=['banner_title_mode', 'banner_text_mode'])
        partial = self._trigger()
        self.assertEqual(partial['bannerTitle'], '')
        self.assertEqual(partial['bannerText'], 'FE-BANNER-MODE')
        self.assertIs(partial['bannerHidden'], False)

        self.city.banner_title_mode = ' FE-TITLE-MODE '
        self.city.banner_text_mode = 'FE-TEXT-MODE'
        self.city.save(update_fields=['banner_title_mode', 'banner_text_mode'])
        filled = self._trigger()
        self.assertEqual(filled['bannerTitle'], 'FE-TITLE-MODE')
        self.assertEqual(filled['bannerText'], 'FE-TEXT-MODE')
        self.assertIs(filled['bannerHidden'], False)
        self.assertNotEqual(filled['bannerTitle'], 'FE-BANNER-TITLE')

        self._mode(False)
        restored = self._trigger()
        self.assertEqual(restored['bannerTitle'], 'FE-BANNER-TITLE')
        self.assertEqual(restored['bannerText'], 'FE-BANNER-TEXT')
        self.assertIs(restored['bannerHidden'], False)

    def test_city_pages_use_mode_meta(self):
        page = CitiesPage.load()
        intro = 'FE-CITIES-INTRO-' + ('X' * 180)
        page.title = 'FE-CITIES-TITLE'
        page.intro = intro
        page.seo_title = ''
        page.seo_description = ''
        page.seo_title_mode = ''
        page.seo_description_mode = ''
        page.title_mode = ''
        page.intro_mode = ''
        page.save()

        self._mode(False)
        listed = self.client.get(reverse('network:city_list'))
        self.assertEqual(listed.context['page_title'], 'FE-CITIES-TITLE')
        self.assertEqual(listed.context['page_description'], intro[:160])

        detail = self.client.get(reverse('network:city_detail', kwargs={'slug': self.city.slug}))
        self.assertEqual(detail.context['page_title'], 'FE-CITY-SEO')
        self.assertEqual(detail.context['page_description'], 'FE-CITY-SEOD')
        self.assertEqual(detail.context['breadcrumb_items'][-1]['title'], 'FE-CITY')

        self._mode(True)
        listed = self.client.get(reverse('network:city_list'))
        self.assertEqual(listed.context['page_title'], NEUTRAL_DESCRIPTION)
        self.assertEqual(listed.context['page_description'], NEUTRAL_DESCRIPTION)
        self.assertNotIn('FE-CITIES-TITLE', listed.context['page_title'])
        self.assertNotIn('FE-CITIES-INTRO', listed.context['page_description'])

        detail = self.client.get(reverse('network:city_detail', kwargs={'slug': self.city.slug}))
        self.assertEqual(detail.context['page_title'], NEUTRAL_DESCRIPTION)
        self.assertEqual(detail.context['page_description'], NEUTRAL_DESCRIPTION)
        self.assertEqual(detail.context['breadcrumb_items'][-1]['title'], '')
        self.assertNotIn('FE-CITY-SEO', detail.context['page_title'])
        self.assertNotIn('FE-CITY', detail.context['page_title'])
        self.assertNotIn('FE-CITY-SEOD', detail.context['page_description'])

        self.city.seo_title_mode = 'FE-CITY-TITLE-MODE'
        self.city.seo_description_mode = 'FE-CITY-DESC-MODE'
        self.city.save(update_fields=['seo_title_mode', 'seo_description_mode'])
        intro_mode = 'FE-CITIES-INTRO-MODE-' + ('Y' * 180)
        page.title_mode = ''
        page.intro_mode = intro_mode
        page.seo_title_mode = 'FE-CITIES-SEO-MODE'
        page.seo_description_mode = ''
        page.save(update_fields=[
            'title_mode', 'intro_mode', 'seo_title_mode', 'seo_description_mode',
        ])
        listed = self.client.get(reverse('network:city_list'))
        self.assertEqual(listed.context['page_title'], 'FE-CITIES-SEO-MODE')
        self.assertEqual(listed.context['page_description'], intro_mode[:160])
        self.assertNotIn('FE-CITIES-INTRO-X', listed.context['page_description'])
        self.assertNotContains(listed, 'FE-CITIES-TITLE')
        self.assertContains(listed, 'FE-CITIES-SEO-MODE')

        self.city.name_mode = 'FE-NAME-MODE'
        self.city.seo_title_mode = ''
        self.city.save(update_fields=['name_mode', 'seo_title_mode'])
        detail = self.client.get(
            reverse('network:city_detail', kwargs={'slug': self.city.slug}),
        )
        self.assertEqual(detail.context['page_title'], 'FE-NAME-MODE')
        self.assertEqual(detail.context['page_description'], 'FE-CITY-DESC-MODE')
        self.assertEqual(detail.context['breadcrumb_items'][-1]['title'], 'FE-NAME-MODE')
        self.assertNotIn('FE-CITY-SEO', detail.context['page_title'])
        self.assertContains(detail, '<h1 class="page-hero__title">FE-NAME-MODE</h1>')
        self.assertNotContains(detail, '<h1 class="page-hero__title">FE-CITY</h1>')

        self._mode(False)
        detail = self.client.get(reverse('network:city_detail', kwargs={'slug': self.city.slug}))
        self.assertEqual(detail.context['page_title'], 'FE-CITY-SEO')
        self.assertEqual(detail.context['page_description'], 'FE-CITY-SEOD')
        self.assertEqual(detail.context['breadcrumb_items'][-1]['title'], 'FE-CITY')

    def test_reviews_page_meta_has_no_original_or(self):
        page = ReviewsPage.load()
        page.seo_title = 'FE-REV-SEO'
        page.seo_description = ''
        page.title = 'FE-REV-TITLE'
        page.seo_title_mode = ''
        page.seo_description_mode = ''
        page.title_mode = ''
        page.save()
        self._mode(False)
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.context['page_title'], 'FE-REV-SEO')
        self.assertEqual(response.context['page_description'], 'FE-REV-TITLE')

        self._mode(True)
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.context['page_title'], NEUTRAL_DESCRIPTION)
        self.assertEqual(response.context['page_description'], NEUTRAL_DESCRIPTION)
        self.assertNotIn('FE-REV-SEO', response.context['page_title'])
        self.assertNotIn('FE-REV-TITLE', response.context['page_description'])

        page.seo_title_mode = 'FE-REV-TITLE-MODE'
        page.seo_description_mode = 'FE-REV-DESC-MODE'
        page.save(update_fields=['seo_title_mode', 'seo_description_mode'])
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.context['page_title'], 'FE-REV-TITLE-MODE')
        self.assertEqual(response.context['page_description'], 'FE-REV-DESC-MODE')
        self.assertContains(response, 'FE-REV-TITLE-MODE')
        self.assertNotContains(response, '>FE-REV-TITLE<')
        self._mode(False)
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.context['page_title'], 'FE-REV-SEO')
        self.assertEqual(response.context['page_description'], 'FE-REV-TITLE')

    def test_article_art_layout_mode(self):
        category = Category.objects.create(name='FE-CAT', slug='fe-cat')
        post = Post.objects.create(
            category=category,
            title='FE-POST-TITLE',
            slug='fe-post',
            excerpt='FE-POST-EXCERPT',
            body='FE-POST-BODY',
            seo_title='FE-POST-SEO',
            seo_description='FE-POST-SEOD',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        url = reverse('blog:post_detail', kwargs={'slug': post.slug})

        def art_of():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for key in _ART_KEYS:
                response.context[key]
            return response

        with patch('src.blog.models.Post.article_layout', return_value=_LAYOUT):
            self._mode(False)
            response = art_of()
            art = response.context['art']
            layout = art['layout']
            self.assertIn('layout', art)
            self.assertIn('layout_mode', art)
            self.assertEqual(set(art), set(_LAYOUT) | {'layout', 'layout_mode'})
            self.assertEqual(art['h1a'], layout['h1a'])
            for key, value in _LAYOUT.items():
                self.assertEqual(art[key], value)
            self.assertEqual(layout, _LAYOUT)
            self.assertEqual(art['layout_mode'], _LAYOUT)
            self.assertContains(response, f'article-banner__title">{layout["h1a"]}')
            self.assertEqual(response.context['page_title'], 'FE-POST-SEO')
            self.assertEqual(response.context['page_description'], 'FE-POST-SEOD')
            self.assertEqual(response.context['breadcrumb_items'][-1]['title'], 'FE-H1A FE-H1B')

            self._mode(True)
            response = art_of()
            art = response.context['art']
            self.assertEqual(art['h1a'], art['layout']['h1a'])
            self.assertEqual(art['layout'], _LAYOUT)
            self.assertIsNot(art['layout_mode'], art['layout'])
            mode = art['layout_mode']
            self.assertEqual(mode['h1a'], '')
            self.assertEqual(mode['h1b'], '')
            self.assertEqual(mode['lead'], '')
            self.assertEqual(mode['read'], '')
            self.assertEqual(mode['fig_cap'], '')
            self.assertEqual(mode['fig_url'], '')
            self.assertEqual(mode['sections'], [{
                'h': '',
                'p': [''],
                'list': [''],
                'fig': None,
            }])
            self.assertIsNone(mode['plain'])
            blob = '\n'.join(_strings(mode))
            for token in ('FE-H1A', 'FE-H1B', 'FE-LEAD', 'FE-SEC', 'FE-P', 'FE-LI', 'FE-CAP'):
                self.assertNotIn(token, blob)
            self.assertEqual(response.context['page_title'], NEUTRAL_DESCRIPTION)
            self.assertEqual(response.context['page_description'], NEUTRAL_DESCRIPTION)
            self.assertEqual(response.context['breadcrumb_items'][-1]['title'], '')
            self.assertNotIn('FE-POST-TITLE', response.context['page_title'])
            self.assertNotIn('FE-POST-EXCERPT', response.context['page_description'])

            with _attrs(Post, h1a_mode='  FE-H1A-MODE  ', h1b_mode='FE-H1B-MODE', lead_mode='FE-LEAD-MODE'):
                response = art_of()
                mode = response.context['art']['layout_mode']
                self.assertEqual(mode['h1a'], 'FE-H1A-MODE')
                self.assertEqual(mode['h1b'], 'FE-H1B-MODE')
                self.assertEqual(mode['lead'], 'FE-LEAD-MODE')
                self.assertEqual(mode['sections'][0]['h'], '')
                self.assertEqual(response.context['art']['layout']['h1a'], 'FE-H1A')
                self.assertEqual(
                    response.context['breadcrumb_items'][-1]['title'],
                    'FE-H1A-MODE FE-H1B-MODE',
                )

            post.seo_title_mode = 'FE-POST-SEO-MODE'
            post.excerpt_mode = 'FE-EXCERPT-MODE'
            post.seo_description_mode = ''
            post.title_mode = ''
            post.save(update_fields=[
                'seo_title_mode', 'excerpt_mode', 'seo_description_mode', 'title_mode',
            ])
            response = art_of()
            self.assertEqual(response.context['page_title'], 'FE-POST-SEO-MODE')
            self.assertEqual(response.context['page_description'], 'FE-EXCERPT-MODE')
            self.assertContains(response, 'FE-EXCERPT-MODE')
            self.assertNotContains(response, 'FE-POST-EXCERPT')
            self._mode(False)
            response = art_of()
            self.assertEqual(response.context['art']['layout_mode']['h1a'], 'FE-H1A')
            self.assertEqual(response.context['page_title'], 'FE-POST-SEO')
            self.assertEqual(response.context['page_description'], 'FE-POST-SEOD')

    def test_services_list_home_page_and_block_mode_keys(self):
        Service.objects.update(
            block_text_mode='',
            block_points_mode='',
            block_cta_mode='',
            short_desc_mode='',
        )
        Service.objects.create(
            title='FE-SVC',
            slug='fe-svc',
            short_desc='FE-SHORT',
            exchange_safe=True,
        )
        for enabled in (False, True):
            self._mode(enabled)
            response = self.client.get(reverse('content:services'))
            self.assertEqual(response.context['home_page'].pk, HomePage.load().pk)
            services = response.context['services']
            self.assertTrue(services)
            for svc in services:
                self.assertEqual(svc.block_text_mode, '')
                self.assertEqual(svc.block_points_mode, '')
                self.assertEqual(svc.block_cta_mode, '')

        row = Service.objects.get(slug='fe-svc')
        row.block_text_mode = 'FE-BLOCK'
        row.block_points_mode = ''
        row.block_cta_mode = 'FE-CTA'
        row.save(update_fields=['block_text_mode', 'block_points_mode', 'block_cta_mode'])
        self._mode(True)
        empty = self.client.get(reverse('content:services'))
        self.assertNotContains(empty, 'FE-SHORT')
        response = empty
        found = {item.slug: item for item in response.context['services']}
        svc = found['fe-svc']
        self.assertEqual(svc.block_text_mode, 'FE-BLOCK')
        self.assertEqual(svc.block_points_mode, '')
        self.assertEqual(svc.block_cta_mode, 'FE-CTA')
        self.assertContains(response, 'FE-BLOCK')
        self.assertContains(response, 'FE-CTA')
        self.assertNotContains(response, 'FE-SHORT')
