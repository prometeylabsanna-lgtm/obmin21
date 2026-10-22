import os

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import Service, ServicesPage
from src.core.models import SiteSettings
from src.core.tests.test_exchange_admin import _flags
from src.core.exchange_preview import build_hide_report
from src.network.models import City
from src.rates.models import CurrencyPair

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS', 'VERCEL')


class ExchangePreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='exchange-preview',
            email='exchange-preview@example.com',
            password='pass-12345',
        )

    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(
            exchange_only=False,
            exchange_only_since=None,
        )
        cache.clear()
        self.client.force_login(self.user)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def test_preview_lists_hidden_records_urls_blocks_and_warnings(self):
        page = ServicesPage.load()
        page.intro_mode = 'Лише готівка у відділенні'
        page.hero_text_mode = 'Обмін USDT у касі'
        page.save(update_fields=['intro_mode', 'hero_text_mode'])
        settings_row = SiteSettings.objects.get(pk=1)
        settings_row.footer_copy = 'Демо криптовалюта у футері'
        settings_row.save(update_fields=['footer_copy'])
        City.objects.create(
            name='Місто етап 8',
            slug='misto-etap-8',
            banner_text='Потрібен переказ готівки',
        )
        category = Category.objects.create(name='Рубрика етап 8', slug='rubryka-etap-8')
        mixed = Category.objects.create(name='Змішана етап 8', slug='zmishana-etap-8')
        empty = Category.objects.create(name='Порожня етап 8', slug='porozhnia-etap-8')
        hidden_post = Post.objects.create(
            category=category,
            title='Прихована стаття етап 8',
            slug='prykhovana-etap-8',
            body='Приховано',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        linked = Post.objects.create(
            category=category,
            title='Ще прихована етап 8',
            slug='shche-prykhovana-etap-8',
            body='Теж приховано',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        draft = Post.objects.create(
            category=category,
            title='Чернетка етап 8',
            slug='chernetka-etap-8',
            body='криптовалюта',
            status=Post.Status.DRAFT,
            exchange_safe=False,
        )
        visible = Post.objects.create(
            category=mixed,
            title='Видима стаття етап 8',
            slug='vydyma-etap-8',
            body='Курс біткоїна <a href="/blog/prykhovana-etap-8/">далі</a>',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        visible.related_posts.add(linked)
        Post.objects.create(
            category=mixed,
            title='Ще видима етап 8',
            slug='shche-vydyma-etap-8',
            body='Лише готівка',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        active_pair = CurrencyPair.objects.create(
            code='BTC',
            name='Біткоїн',
            slug='btc-etap-8',
            exchange_safe=False,
            is_active=True,
        )
        CurrencyPair.objects.create(
            code='ETH',
            name='Ефір',
            slug='eth-inactive-etap-8',
            exchange_safe=False,
            is_active=False,
        )
        safe_pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-etap-8',
            exchange_safe=True,
            is_active=True,
        )
        Service.objects.create(
            title='Послуга без режиму етап 8',
            slug='bez-rezhymu-etap-8',
            short_desc='Текст',
            exchange_safe=False,
        )
        Service.objects.create(
            title='Послуга з режимом етап 8',
            slug='z-rezhymom-etap-8',
            short_desc='Текст',
            exchange_safe=True,
            block_text_mode='Готівка',
            block_points_mode='Пункт',
            block_cta_mode='Курс',
        )
        before = _flags()
        report = build_hide_report()
        self.assertEqual(_flags(), before)
        labels = {
            group.title: [row.label for row in group.records]
            for group in report.groups
        }
        self.assertIn('Прихована стаття етап 8', labels['Статті'])
        self.assertIn('Послуга без режиму етап 8', labels['Картки послуг'])
        self.assertNotIn('Послуга з режимом етап 8', labels['Картки послуг'])
        urls = {row.url for row in report.urls}
        self.assertIn(reverse('blog:post_detail', kwargs={'slug': hidden_post.slug}), urls)
        self.assertIn(reverse('rates:pair_detail', kwargs={'slug': active_pair.slug}), urls)
        self.assertIn(
            reverse('blog:category', kwargs={'category_slug': category.slug}),
            urls,
        )
        self.assertNotIn(reverse('blog:post_detail', kwargs={'slug': visible.slug}), urls)
        self.assertNotIn(reverse('blog:post_detail', kwargs={'slug': draft.slug}), urls)
        self.assertNotIn(
            reverse('rates:pair_detail', kwargs={'slug': 'eth-inactive-etap-8'}),
            urls,
        )
        self.assertNotIn(reverse('rates:pair_detail', kwargs={'slug': safe_pair.slug}), urls)
        self.assertNotIn(
            reverse('blog:category', kwargs={'category_slug': mixed.slug}),
            urls,
        )
        self.assertNotIn(
            reverse('blog:category', kwargs={'category_slug': empty.slug}),
            urls,
        )
        blocks = {(row.object_label, row.field_label) for row in report.blocks}
        self.assertIn(
            ('Послуга без режиму етап 8', 'Текст блоку для режиму «Лише обмін»'),
            blocks,
        )
        self.assertNotIn(
            ('Послуга з режимом етап 8', 'Текст блоку для режиму «Лише обмін»'),
            blocks,
        )
        self.assertNotIn(
            'Вступ для режиму «Лише обмін»',
            [row.field_label for row in report.blocks],
        )
        mode_places = ' '.join(row.place + row.words for row in report.mode_warnings)
        self.assertIn('Текст банера для режиму «Лише обмін»', mode_places)
        self.assertIn('usdt', mode_places)
        settings_blob = ' '.join(
            row.place + row.words for row in report.settings_warnings
        )
        self.assertIn('Рядок копірайту внизу', settings_blob)
        self.assertIn('крипт', settings_blob)
        city_blob = ' '.join(row.place + row.words for row in report.city_warnings)
        self.assertIn('Місто етап 8', city_blob)
        self.assertIn('переказ', city_blob)
        post_blob = ' '.join(row.place + row.words for row in report.post_warnings)
        self.assertIn('Видима стаття етап 8', post_blob)
        self.assertIn('біткоїн', post_blob)
        self.assertNotIn('Чернетка етап 8', post_blob)
        link_pairs = {(row.source, row.target, row.url) for row in report.links}
        hidden_url = reverse('blog:post_detail', kwargs={'slug': hidden_post.slug})
        linked_url = reverse('blog:post_detail', kwargs={'slug': linked.slug})
        self.assertIn(
            ('Видима стаття етап 8', 'Прихована стаття етап 8', hidden_url),
            link_pairs,
        )
        self.assertIn(
            ('Видима стаття етап 8', 'Ще прихована етап 8', linked_url),
            link_pairs,
        )
        page_html = self.client.get(
            reverse('admin:core_sitesettings_exchange_only_preview', args=[1]),
        )
        self.assertEqual(page_html.status_code, 200)
        self.assertContains(page_html, 'Що буде сховано')
        self.assertContains(page_html, 'Сховані записи')
        self.assertContains(page_html, 'Адреси, які стануть недоступними')
        self.assertContains(page_html, 'Блоки, які зникнуть')
        self.assertContains(page_html, 'Попередження: стоп-слова в полях для режиму')
        self.assertContains(page_html, 'Попередження: стоп-слова в налаштуваннях')
        self.assertContains(page_html, 'Попередження: стоп-слова в містах')
        self.assertContains(page_html, 'Попередження: стоп-слова у видимих статтях')
        self.assertContains(page_html, 'Попередження: посилання з видимих статей на приховані')
        self.assertContains(page_html, 'Прихована стаття етап 8')
        self.assertContains(page_html, 'Підтвердити увімкнення')
        self.assertContains(page_html, 'csrfmiddlewaretoken')
        self.assertEqual(_flags(), before)
