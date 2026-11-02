from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from src.blog.models import Category, Post
from src.content.models import FaqItem
from src.core.admin_mixins import _sanitize_rich_fields
from src.core.html_sanitize import sanitize_rich_html
from src.core.templatetags.content_format import rich_html
from src.reviews.forms import ReviewForm
from src.reviews.models import Review

_XSS = (
    '<p>Ок</p><script>alert(1)</script>'
    '<img src=x onerror=alert(1)>'
    '<a href="javascript:alert(1)">x</a>'
)


class HtmlSanitizeUnitTests(TestCase):
    def test_strips_script_onerror_and_javascript_urls(self):
        cleaned = sanitize_rich_html(_XSS)
        self.assertIn('<p>Ок</p>', cleaned)
        self.assertNotIn('<script', cleaned.lower())
        self.assertNotIn('onerror', cleaned.lower())
        self.assertNotIn('javascript:', cleaned.lower())
        self.assertNotIn('alert(1)', cleaned)

    def test_rich_html_filter_sanitizes(self):
        html = str(rich_html(_XSS))
        self.assertNotIn('<script', html.lower())
        self.assertNotIn('onerror', html.lower())
        self.assertNotIn('javascript:', html.lower())


class ReviewPlainTextTests(TestCase):
    def test_form_strips_tags_and_page_escapes(self):
        form = ReviewForm(data={
            'name': 'Олег',
            'text': '<script>alert(1)</script><b>Добре</b>',
            'city_name': 'Київ',
            'phone': '',
            'consent': True,
            'rating': 5,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['text'], 'Добре')
        review = form.save(commit=False)
        review.is_published = True
        review.published_at = timezone.now()
        review.save()
        self.assertEqual(Review.objects.get(pk=review.pk).text, 'Добре')
        response = self.client.get('/vidhuky/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Добре', body)
        self.assertNotIn('<script>alert', body)
        self.assertNotIn('<b>Добре</b>', body)


class AdminRichSaveSanitizeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='xss-admin',
            email='xss@example.com',
            password='pass-12345',
        )
        cls.category = Category.objects.create(name='Курси', slug='kursy-xss')

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_post_body_sanitized_on_admin_save_and_page(self):
        post = Post(
            category=self.category,
            title='XSS пост',
            slug='xss-post',
            body=_XSS,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        _sanitize_rich_fields(post, frozenset({'body', 'excerpt', 'faq'}))
        post.save()
        stored = Post.objects.get(pk=post.pk).body
        self.assertNotIn('<script', stored.lower())
        self.assertNotIn('onerror', stored.lower())
        self.assertNotIn('javascript:', stored.lower())
        page = self.client.get(f'/blog/{post.slug}/')
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertNotIn('<script>alert', html)
        self.assertNotIn('onerror', html.lower())

    def test_faq_answer_sanitized(self):
        item = FaqItem(question='XSS?', answer=_XSS, is_active=True, sort_order=1)
        _sanitize_rich_fields(item, frozenset({'answer'}))
        item.save()
        stored = FaqItem.objects.get(pk=item.pk).answer
        self.assertNotIn('<script', stored.lower())
        self.assertNotIn('onerror', stored.lower())
