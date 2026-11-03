from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse

from src.blog.models import Category, Post
from src.core.models import SiteSettings
from src.leads.models import ContactMessage, ExchangeRequest

_GIF = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04'
        b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')


class R2Base(TestCase):
    def setUp(self):
        cache.clear()
        SiteSettings.objects.get_or_create(pk=1)
        self.cat = Category.objects.create(name='C', slug='c')


class OgImageTests(R2Base):
    def test_article_cover_is_og_image(self):
        import tempfile
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            post = Post.objects.create(
                category=self.cat, title='OG', slug='og-post', body='Текст.',
                status=Post.Status.PUBLISHED, exchange_safe=True,
                cover=SimpleUploadedFile('c.gif', _GIF, content_type='image/gif'),
            )
            r = self.client.get(reverse('blog:post_detail', kwargs={'slug': post.slug}))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(f'<meta property="og:image" content="https://obmin21.com{post.cover.url}"', html)
        self.assertNotIn('og-obmin21', html.split('og:image"')[1][:120])


class HoneypotTests(R2Base):
    def test_contact_honeypot_saves_nothing(self):
        r = self.client.post(reverse('leads:contact_submit'), {
            'name': 'Бот', 'phone': '+380501112233', 'message': 'spam',
            'consent': 'on', 'website': 'http://spam.example',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b'')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_request_honeypot_saves_nothing(self):
        r = self.client.post(reverse('leads:request_modal'), {'website': 'x', 'phone': '+380501112233'})
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Заявку прийнято')
        self.assertEqual(ExchangeRequest.objects.count(), 0)

    def test_forms_have_hidden_field(self):
        for name in ('partials/modal_request.html',):  # contact modal has no inputs by design
            with open(f'templates/{name}', encoding='utf-8') as fh:
                self.assertIn('name="website" class="form__hp"', fh.read(), name)


class RawTagTests(R2Base):
    def test_brand_mark_strips_html_and_escapes(self):
        out = Template('{% load content_format %}{{ v|brand_mark }}').render(Context({
            'v': '<p>Курс долара</p><p>Обмін21 &amp; <script>alert(1)</script>ок</p>',
        }))
        self.assertNotIn('&lt;p&gt;', out)
        self.assertNotIn('<p>', out)
        self.assertNotIn('script', out)
        self.assertIn('Курс долара<br>', out)
        self.assertIn('&amp;', out)

    def test_article_lead_with_html_excerpt_has_no_raw_tags(self):
        post = Post.objects.create(
            category=self.cat, title='T', slug='html-lead', body='Текст.',
            excerpt='<p>Курс долара залишається</p>',
            status=Post.Status.PUBLISHED, exchange_safe=True,
        )
        r = self.client.get(reverse('blog:post_detail', kwargs={'slug': post.slug}))
        self.assertNotContains(r, '&lt;p&gt;')
        self.assertContains(r, 'Курс долара залишається')
