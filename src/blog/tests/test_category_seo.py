from django.test import TestCase
from django.utils import timezone

from src.blog.admin import CategoryAdmin
from src.blog.models import Category, Post
from src.blog.views import category_page_copy
from src.core.tests.test_eo_default_mode import forced_exchange_client


def _category(slug, **fields):
    category = Category.objects.create(name='ZZ-META', slug=slug, **fields)
    Post.objects.create(
        category=category,
        title='Нотатка',
        slug=f'{slug}-post',
        body='Текст',
        status=Post.Status.PUBLISHED,
        exchange_safe=True,
        published_at=timezone.now(),
    )
    return category


class CategorySeoFieldTests(TestCase):
    def test_admin_and_model_expose_blank_seo_fields(self):
        title = Category._meta.get_field('seo_title')
        description = Category._meta.get_field('seo_description')
        self.assertEqual(title.max_length, 255)
        self.assertTrue(title.blank)
        self.assertTrue(description.blank)
        self.assertIn('seo_title', CategoryAdmin.fields)
        self.assertIn('seo_description', CategoryAdmin.fields)

    def test_blank_fields_keep_name_and_rubric_description(self):
        category = _category('zz-meta-blank', seo_title='', seo_description='   ')
        url = '/blog/kategoriya/zz-meta-blank/'
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                with forced_exchange_client(enabled) as client:
                    response = client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertRegex(html, r'<h1 class="blog-hero__title">ZZ-META</h1>')
                self.assertRegex(html, r'<title>\s*ZZ-META · Обмін21\s*</title>')
                self.assertEqual(
                    response.context['page_description'],
                    'Статті рубрики ZZ-META.',
                )
                self.assertIn(
                    '<meta name="description" content="Статті рубрики ZZ-META.">',
                    html,
                )
                copy = category_page_copy(category, response.wsgi_request)
                self.assertEqual(copy['title'], 'ZZ-META')
                self.assertEqual(copy['heading'], 'ZZ-META')
                self.assertEqual(copy['description'], 'Статті рубрики ZZ-META.')

    def test_seo_fields_override_title_and_description(self):
        category = _category(
            'zz-meta-seo',
            seo_title='SEO заголовок рубрики',
            seo_description='SEO опис рубрики для пошуку.',
        )
        url = '/blog/kategoriya/zz-meta-seo/'
        with forced_exchange_client(False) as client:
            response = client.get(url)
            copy = category_page_copy(category, response.wsgi_request)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertRegex(html, r'<h1 class="blog-hero__title">ZZ-META</h1>')
        self.assertRegex(
            html,
            r'<title>\s*SEO заголовок рубрики · Обмін21\s*</title>',
        )
        self.assertEqual(
            response.context['page_title'],
            'SEO заголовок рубрики',
        )
        self.assertEqual(
            response.context['page_description'],
            'SEO опис рубрики для пошуку.',
        )
        self.assertIn(
            '<meta name="description" content="SEO опис рубрики для пошуку.">',
            html,
        )
        self.assertEqual(copy['heading'], 'ZZ-META')
        self.assertEqual(copy['title'], 'SEO заголовок рубрики')
        self.assertEqual(copy['description'], 'SEO опис рубрики для пошуку.')

        with forced_exchange_client(True) as client:
            exchange = client.get(url)
        self.assertEqual(exchange.status_code, 200)
        exchange_html = exchange.content.decode()
        self.assertRegex(exchange_html, r'<title>\s*ZZ-META · Обмін21\s*</title>')
        self.assertEqual(
            exchange.context['page_description'],
            'Статті рубрики ZZ-META.',
        )
        self.assertRegex(exchange_html, r'<h1 class="blog-hero__title">ZZ-META</h1>')
