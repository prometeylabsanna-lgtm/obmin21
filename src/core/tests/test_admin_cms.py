from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.core.vercel_admin import ensure_vercel_admin


class AdminPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='editor',
            email='editor@example.com',
            password='pass-12345',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_header_change_has_ukrainian_tabs(self):
        resp = self.client.get(reverse('admin:core_headersettings_changelist'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Контент')
        self.assertContains(resp, 'Оформлення')
        self.assertContains(resp, 'Логотип у шапці')
        self.assertContains(resp, 'images/logo.png')
        self.assertContains(resp, 'cms-color__swatch')
        self.assertContains(resp, 'type="color"')

    def test_home_change_and_theme_css(self):
        HomePage.load()
        change_url = reverse('admin:content_homepage_change', args=[1])
        resp = self.client.get(change_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Блок «Вигідний курс на USD та EUR»')
        self.assertNotContains(resp, 'Банер після')
        self.assertContains(resp, 'images/coins.png')
        self.assertContains(resp, 'cms-color__swatch')

        post = self.client.post(change_url, {
            'seo_title': 'Головна',
            'seo_description': '',
            'promo_kicker': 'USD та EUR',
            'promo_title': 'Вигідний курс',
            'promo_title_accent': 'USD та EUR',
            'promo_text': 'Обмінюйте валюту за актуальним курсом без зайвих кроків',
            'promo_button': 'Обрати валюту',
            'seo_block_title': 'Обмін валют',
            'seo_block_body': '<p>Текст</p>',
            'color_bg': '#f3f6fb',
            'color_text': '#052145',
            'color_accent': '#ca8d42',
        }, follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertContains(post, 'Зміни успішно збережено!')
        home = HomePage.objects.get(pk=1)
        self.assertEqual(home.color_bg, '#f3f6fb')

        css = self.client.get(reverse('core:theme_css'))
        self.assertEqual(css.status_code, 200)
        self.assertEqual(css['Content-Type'].split(';')[0], 'text/css')
        self.assertContains(css, '[data-theme="home"]')
        self.assertContains(css, '#f3f6fb')
        self.assertContains(css, '[data-theme="header"]')

    def test_public_home_uses_theme(self):
        SiteSettings.load()
        resp = self.client.get(reverse('core:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-theme="home"')
        self.assertContains(resp, 'data-theme="header"')
        self.assertContains(resp, 'data-theme="footer"')
        self.assertContains(resp, reverse('core:theme_css'))

    def test_admin_login_uses_brand_colors_and_logo(self):
        self.client.logout()
        resp = self.client.get(reverse('admin:login'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'rgb(202, 141, 66)')
        self.assertContains(resp, 'rgb(5, 33, 69)')
        self.assertContains(resp, 'images/logo.png')
        self.assertContains(resp, 'images/favicon-32x32.png')
        self.assertNotContains(resp, 'Панель Обмін21')

    def test_admin_sidebar_uses_site_logo(self):
        resp = self.client.get(reverse('admin:index'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'images/logo.png')
        self.assertContains(resp, 'images/favicon.ico')
        self.assertNotContains(resp, 'Обмін21 — панель редагування')

    def test_ensure_vercel_admin_keeps_session(self):
        ensure_vercel_admin()
        hash_before = User.objects.get(username='admin').password
        self.client.logout()
        self.assertTrue(self.client.login(username='admin', password='admin'))
        ensure_vercel_admin()
        self.assertEqual(User.objects.get(username='admin').password, hash_before)
        resp = self.client.get(reverse('admin:index'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Адміністрування')

    def test_city_home_banner_fields(self):
        from src.network.models import City
        city = City.objects.create(name='Київ', slug='kyiv-cms')
        resp = self.client.get(reverse('admin:network_city_change', args=[city.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Банер на головній')
        self.assertContains(resp, 'Підпис на банері')
        self.assertContains(resp, 'Курси в калькуляторі')

    def test_shared_lists_in_sidebar(self):
        resp = self.client.get(reverse('admin:index'))
        self.assertContains(resp, 'Новини')
        self.assertContains(resp, 'FAQ')
        self.assertContains(resp, reverse('admin:reviews_review_changelist'))
        self.assertContains(resp, reverse('admin:content_faqitem_changelist'))
        self.assertContains(resp, reverse('admin:blog_post_changelist'))
