import os
import re

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import AdvantagesPage, HomePage, HomeStat
from src.core.models import SiteSettings

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_MODULE = re.compile(
    r'<script type="module" src="[^"]*js/modules/count-up\.js\?v=1"></script>',
)
_NUM = re.compile(
    r'<div class="stats-section__num"([^>]*)>(.*?)</div>',
    re.S,
)


class CountUpStatsTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)
        home = HomePage.load()
        home.show_why = True
        home.save(update_fields=['show_why'])
        HomeStat.objects.all().delete()
        HomeStat.objects.create(
            page=home,
            number='7K',
            number_mode='15+',
            text='CU-HOME-OFF-A',
            text_mode='CU-HOME-ON-A',
            exchange_safe=True,
            is_active=True,
            sort_order=0,
        )
        HomeStat.objects.create(
            page=home,
            number='98%',
            number_mode='10+',
            text='CU-HOME-OFF-B',
            text_mode='CU-HOME-ON-B',
            exchange_safe=True,
            is_active=True,
            sort_order=1,
        )
        page = AdvantagesPage.load()
        page.stat_1_title = '7K'
        page.stat_1_text = 'CU-ADV-OFF-A'
        page.stat_1_text_mode = 'CU-ADV-ON-A'
        page.stat_2_title = '20+'
        page.stat_2_text = 'CU-ADV-OFF-B'
        page.stat_2_text_mode = 'CU-ADV-ON-B'
        page.stat_3_title = '98%'
        page.stat_3_text = 'CU-ADV-OFF-C'
        page.stat_3_text_mode = 'CU-ADV-ON-C'
        page.stat_4_title = '10+'
        page.stat_4_text = 'CU-ADV-OFF-D'
        page.stat_4_text_mode = 'CU-ADV-ON-D'
        page.save()

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

    def _html(self, url_name):
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _stats_block(self, html):
        match = re.search(
            r'<section class="stats-section\b[\s\S]*?</section>',
            html,
        )
        self.assertIsNotNone(match)
        return match.group(0)

    def _numbers(self, block):
        found = _NUM.findall(block)
        self.assertTrue(found)
        texts = []
        for attrs, text in found:
            self.assertIn('data-count-up', attrs)
            texts.append(text.strip())
        self.assertEqual(block.count('data-count-up'), len(found))
        return texts

    def _assert_module(self, html):
        self.assertEqual(len(_MODULE.findall(html)), 1)

    def test_home_and_advantages_mark_stats_in_both_modes(self):
        self._mode(False)
        home_off = self._html('core:home')
        self._assert_module(home_off)
        home_block = self._stats_block(home_off)
        self.assertEqual(self._numbers(home_block), ['7K', '98%'])
        self.assertIn('CU-HOME-OFF-A', home_block)
        self.assertIn('CU-HOME-OFF-B', home_block)
        self.assertNotIn('CU-HOME-ON-A', home_block)
        self.assertNotIn('CU-HOME-ON-B', home_block)

        adv_off = self._html('content:advantages')
        self._assert_module(adv_off)
        adv_block = self._stats_block(adv_off)
        self.assertEqual(self._numbers(adv_block), ['7K', '20+', '98%', '10+'])
        self.assertIn('CU-ADV-OFF-A', adv_block)
        self.assertIn('CU-ADV-OFF-D', adv_block)
        self.assertNotIn('CU-ADV-ON-A', adv_block)
        self.assertNotIn('CU-ADV-ON-D', adv_block)

        self._mode(True)
        home_on = self._html('core:home')
        self._assert_module(home_on)
        home_mode = self._stats_block(home_on)
        self.assertEqual(self._numbers(home_mode), ['15+', '10+'])
        self.assertIn('CU-HOME-ON-A', home_mode)
        self.assertIn('CU-HOME-ON-B', home_mode)
        self.assertNotIn('CU-HOME-OFF-A', home_mode)
        self.assertNotIn('CU-HOME-OFF-B', home_mode)

        adv_on = self._html('content:advantages')
        self._assert_module(adv_on)
        adv_mode = self._stats_block(adv_on)
        self.assertEqual(self._numbers(adv_mode), ['7K', '20+', '98%', '10+'])
        self.assertIn('CU-ADV-ON-A', adv_mode)
        self.assertIn('CU-ADV-ON-D', adv_mode)
        self.assertNotIn('CU-ADV-OFF-A', adv_mode)
        self.assertNotIn('CU-ADV-OFF-D', adv_mode)
        self.assertNotIn('display:none', ''.join(adv_mode.lower().split()))

    def test_home_fallback_number_is_marked_outside_mode(self):
        HomeStat.objects.all().delete()
        self._mode(False)
        shown = self._html('core:home')
        self._assert_module(shown)
        self.assertEqual(self._numbers(self._stats_block(shown)), ['7K'])

        self._mode(True)
        hidden = self._html('core:home')
        self._assert_module(hidden)
        self.assertNotIn('stats-section__num', hidden)
        self.assertNotIn('7K', hidden)
        self.assertNotIn('display:none', ''.join(hidden.lower().split()))

    def test_module_observes_viewport_and_reduced_motion(self):
        source = (
            settings.BASE_DIR / 'src/core/static/js/modules/count-up.js'
        ).read_text(encoding='utf-8')
        self.assertIn('prefers-reduced-motion', source)
        self.assertIn('IntersectionObserver', source)
        self.assertIn('.stats-section [data-count-up]', source)
        self.assertNotIn('7K', source)
        self.assertNotIn('15+', source)
        self.assertNotIn('98%', source)
