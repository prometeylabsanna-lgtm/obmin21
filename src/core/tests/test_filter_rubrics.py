import os

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.blog.selectors import visible_categories
from src.core.exchange_stopwords import STOP_WORDS, matches_stop_words
from src.core.models import SiteSettings

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class _ModeCase(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)


def _published(category, slug, *, exchange_safe):
    return Post.objects.create(
        category=category,
        title=slug,
        slug=slug,
        body='Текст',
        status=Post.Status.PUBLISHED,
        exchange_safe=exchange_safe,
    )


class RubricVisibilityTests(_ModeCase):
    def setUp(self):
        super().setUp()
        SiteSettings.objects.filter(pk=1).update(hidden_page_status=503)
        self._mode(True)

    def _category(self, slug, name):
        return Category.objects.create(name=name, slug=slug)

    def _slugs(self):
        return set(visible_categories().values_list('slug', flat=True))

    def _category_status(self, slug):
        response = self.client.get(
            reverse('blog:category', kwargs={'category_slug': slug}),
        )
        return response.status_code

    def test_zoloto_with_safe_post_is_hidden(self):
        category = self._category('zoloto', 'Золото')
        _published(category, 'rubric-zoloto-safe', exchange_safe=True)
        self.assertEqual(self._category_status('zoloto'), 404)
        self.assertNotIn('zoloto', self._slugs())

    def test_perekazy_with_safe_post_is_hidden(self):
        category = self._category('perekazy', 'Перекази')
        _published(category, 'rubric-perekazy-safe', exchange_safe=True)
        self.assertEqual(self._category_status('perekazy'), 404)
        self.assertNotIn('perekazy', self._slugs())

    def test_neutral_rubric_with_only_unsafe_posts_is_hidden(self):
        category = self._category('gotivka', 'Готівка')
        self.assertFalse(matches_stop_words(category.slug, category.name))
        _published(category, 'rubric-gotivka-unsafe', exchange_safe=False)
        self.assertEqual(self._category_status('gotivka'), 503)
        self.assertNotIn('gotivka', self._slugs())

    def test_neutral_rubric_with_safe_post_is_public(self):
        category = self._category('kurs-valyut', 'Курс валют')
        self.assertFalse(matches_stop_words(category.slug, category.name))
        _published(category, 'rubric-kurs-safe', exchange_safe=True)
        self.assertEqual(self._category_status('kurs-valyut'), 200)
        self.assertIn('kurs-valyut', self._slugs())

    def test_zoloto_is_public_when_mode_off(self):
        self._mode(False)
        category = self._category('zoloto', 'Золото')
        _published(category, 'rubric-zoloto-off', exchange_safe=True)
        self.assertEqual(self._category_status('zoloto'), 200)
        self.assertIn('zoloto', self._slugs())

    def test_unsafe_post_detail_follows_mode(self):
        category = self._category('novyny', 'Новини')
        self.assertFalse(matches_stop_words(category.slug, category.name))
        post = _published(category, 'rubric-unsafe-detail', exchange_safe=False)
        url = reverse('blog:post_detail', kwargs={'slug': post.slug})
        self.assertEqual(self.client.get(url).status_code, 503)
        self._mode(False)
        self.assertEqual(self.client.get(url).status_code, 200)


class StopWordTests(SimpleTestCase):
    def test_each_stop_word_matches_itself(self):
        for word in STOP_WORDS:
            with self.subTest(word=word):
                self.assertTrue(matches_stop_words(word))
                self.assertTrue(matches_stop_words(word.swapcase()))

    def test_blank_values_do_not_match(self):
        self.assertFalse(matches_stop_words())
        self.assertFalse(matches_stop_words(None))
        self.assertFalse(matches_stop_words(None, '', '   '))

    def test_rubric_names_match_and_neutral_text_does_not(self):
        self.assertTrue(matches_stop_words('zoloto', 'Золото'))
        self.assertTrue(matches_stop_words('perekazy', 'Перекази'))
        self.assertTrue(matches_stop_words('інвестиційне золото'))
        self.assertTrue(matches_stop_words('міжнародні перекази'))
        self.assertTrue(matches_stop_words('  GOLD  '))
        self.assertTrue(matches_stop_words('Crypto'))
        self.assertTrue(matches_stop_words('електронн валют'))
        self.assertFalse(matches_stop_words('zoloto'))
        self.assertFalse(matches_stop_words('perekazy'))
        self.assertFalse(matches_stop_words('Курс валют', 'kurs-valyut'))
        self.assertFalse(matches_stop_words('Готівка', 'gotivka'))
        self.assertFalse(matches_stop_words('Новини', 'novyny'))

    def test_any_argument_matches_but_words_do_not_join(self):
        self.assertTrue(matches_stop_words('novyny', None, '  Bitcoin  '))
        self.assertFalse(matches_stop_words('електронн', 'валют'))
