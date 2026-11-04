from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage


class HomeSliderArrowsTests(TestCase):
    def test_home_renders_slider_arrows_and_script_version(self):
        page = HomePage.load()
        page.show_articles = True
        page.show_reviews = True
        page.save()

        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertEqual(html.count('data-slider-nav="articles"'), 2)
        self.assertEqual(html.count('data-slider-nav="reviews"'), 2)
        self.assertIn('data-slider-prev', html)
        self.assertIn('data-slider-next', html)
        self.assertGreaterEqual(html.count('data-slider-prev'), 4)
        self.assertGreaterEqual(html.count('data-slider-next'), 4)
        self.assertIn('/static/js/pages/home.js?v=17', html)
        self.assertNotIn('js/pages/home.js?v=16', html)

        js = Path(settings.BASE_DIR, 'src/core/static/js/pages/home.js').read_text(encoding='utf-8')
        self.assertNotIn('scrollBy', js)
        self.assertIn('scrollTo', js)
        self.assertIn('aria-disabled', js)
        self.assertIn('data-slider-bound', js)
