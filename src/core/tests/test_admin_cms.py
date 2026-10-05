from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings


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

    def test_home_change_and_theme_css(self):
        HomePage.load()
        change_url = reverse('admin:content_homepage_change', args=[1])
        resp = self.client.get(change_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Банер після блоків курсів')
        self.assertContains(resp, 'Колір фону')

        post = self.client.post(change_url, {
            'seo_title': 'Головна',
            'seo_description': '',
            'cta_title': 'Зафіксуй курс. Забронюй онлайн.',
            'seo_block_title': 'Обмін валют',
            'seo_block_body': '<p>Текст</p>',
            'color_bg': '#f3f6fb',
            'color_text': '#052145',
            'color_accent': '#4e7394',
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
