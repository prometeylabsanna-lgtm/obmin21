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
        promo_url = reverse('admin:content_homepromosettings_change', args=[1])
        resp = self.client.get(promo_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Вигідний курс')
        self.assertNotContains(resp, 'Банер після')
        self.assertContains(resp, 'images/coins.png')

        post = self.client.post(promo_url, {
            'promo_kicker': 'USD та EUR',
            'promo_title': 'Вигідний курс',
            'promo_title_accent': 'USD та EUR',
            'promo_text': 'Обмінюйте валюту за актуальним курсом без зайвих кроків',
            'promo_button': 'Обрати валюту',
        }, follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertContains(post, 'Зміни успішно збережено!')

        search_url = reverse('admin:content_homesearchsettings_change', args=[1])
        theme_post = self.client.post(search_url, {
            'seo_title': 'Головна',
            'seo_description': '',
            'seo_block_title': 'Обмін валют',
            'seo_block_body': '<p>Текст</p>',
            'color_bg': '#f3f6fb',
            'color_text': '#052145',
            'color_accent': '#ca8d42',
        }, follow=True)
        self.assertEqual(theme_post.status_code, 200)
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
        resp = self.client.get(reverse('admin:network_bannercity_change', args=[city.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Банер')
        self.assertContains(resp, 'Підпис на банері')
        self.assertContains(resp, 'Курси на банері')

    def test_shared_lists_in_sidebar(self):
        resp = self.client.get(reverse('admin:index'))
        self.assertContains(resp, 'Банер')
        self.assertContains(resp, 'Документи')
        self.assertContains(resp, reverse('admin:blog_post_changelist'))
        self.assertContains(resp, reverse('admin:content_homefaqsettings_changelist'))
        self.assertContains(resp, reverse('admin:content_homereviewssettings_changelist'))
        html = resp.content.decode()
        self.assertIn('Сторінка Блог', html)
        self.assertNotIn('Заголовок сторінки', html)
        self.assertLess(
            html.find('/admin/content/blogpage/'),
            html.find('/admin/blog/post/'),
        )

    def test_admin_ukrainian_placeholders_and_choices(self):
        index = self.client.get(reverse('admin:index'))
        self.assertContains(index, 'Пошук розділів і сторінок')
        self.assertNotContains(index, 'Search apps and models')

        add = self.client.get(reverse('admin:blog_post_add'))
        self.assertEqual(add.status_code, 200)
        self.assertContains(add, 'Чернетка')
        self.assertContains(add, 'Оберіть значення')
        self.assertNotContains(add, 'Select value')
        self.assertNotContains(add, 'value="draft">draft')
        html = add.content.decode()
        self.assertNotIn('>draft<', html)

        from src.blog.models import Category
        Category.objects.create(name='Поради', slug='porady')
        Category.objects.create(name='Курси', slug='kursy')
        listing = self.client.get(reverse('admin:blog_post_changelist'))
        self.assertContains(listing, 'Введіть запит для пошуку')
        self.assertNotContains(listing, 'Type to search')
        self.assertContains(listing, 'cms-list-filter__select')
        self.assertContains(listing, 'Статус')
        self.assertContains(listing, 'Категорія')
        self.assertNotContains(listing, 'За Статус')
        self.assertNotContains(listing, 'За Категорія')
        self.assertContains(listing, 'selected')
        self.assertNotContains(listing, 'id="changelist-filter"')

        from src.network.models import City
        City.objects.create(name='Київ', slug='kyiv-uk')
        city = self.client.get(reverse('admin:network_bannercity_changelist'), follow=True)
        self.assertNotContains(city, '>General<')
        self.assertContains(city, 'Обрати місто')

    def test_post_slug_is_generated_and_readonly(self):
        from src.blog.models import Category, Post

        category = Category.objects.create(name='Поради', slug='porady')

        add = self.client.get(reverse('admin:blog_post_add'))
        self.assertNotContains(add, 'name="slug"')
        self.assertNotContains(add, '>Slug<')

        created = self.client.post(reverse('admin:blog_post_add'), {
            'title': 'Як вигідно міняти',
            'category': category.pk,
            'status': 'draft',
            'body': '<p>Текст</p>',
            'excerpt': '',
            'seo_title': '',
            'seo_description': '',
            'faq': '',
            'published_at_0': '',
            'published_at_1': '',
        }, follow=True)
        self.assertEqual(created.status_code, 200)
        post = Post.objects.get(title='Як вигідно міняти')
        self.assertEqual(post.slug, 'yak-vyhidno-minyaty')

        change = self.client.get(reverse('admin:blog_post_change', args=[post.pk]))
        self.assertContains(change, 'yak-vyhidno-minyaty')
        self.assertNotContains(change, 'name="slug"')
        self.assertContains(change, 'Код у посиланні')

    def test_blog_page_copy_order_and_category_filter(self):
        from datetime import timedelta

        from django.utils import timezone

        from src.blog.models import Category, Post
        from src.content.models import BlogPage

        page = BlogPage.load()
        page.title = 'Блог'
        page.heading = 'Корисні'
        page.title_accent = 'статті'
        page.intro = 'Пояснюємо, як працює курс валют.'
        page.save()

        visible = Category.objects.create(name='Поради', slug='porady-cms')
        hidden = Category.objects.create(
            name='Архів',
            slug='arkhiv-cms',
            show_in_filter=False,
        )
        now = timezone.now()
        Post.objects.create(
            category=visible,
            title='Старіша',
            slug='starisha',
            body='Текст',
            status=Post.Status.PUBLISHED,
            published_at=now - timedelta(days=2),
        )
        Post.objects.create(
            category=visible,
            title='Найсвіжіша',
            slug='naysvizhisha',
            body='Текст',
            status=Post.Status.PUBLISHED,
            published_at=now,
        )

        blog = self.client.get(reverse('blog:post_list'))
        self.assertContains(blog, 'Корисні')
        self.assertContains(blog, 'статті')
        self.assertContains(blog, 'Пояснюємо, як працює курс валют.')
        self.assertContains(blog, 'Поради')
        self.assertNotContains(blog, 'Архів')
        html = blog.content.decode()
        self.assertLess(html.find('Найсвіжіша'), html.find('Старіша'))
        self.assertEqual(
            self.client.get(reverse('blog:category', args=['arkhiv-cms'])).status_code,
            404,
        )

        admin_page = self.client.get(
            reverse('admin:content_blogpage_changelist'),
            follow=True,
        )
        self.assertContains(admin_page, 'Мітка')
        self.assertContains(admin_page, 'Акцент у заголовку')
        self.assertContains(admin_page, 'name="heading"')

        cat_admin = self.client.get(
            reverse('admin:blog_category_change', args=[hidden.pk]),
        )
        self.assertContains(cat_admin, 'Показувати у фільтрі на сторінці')

    def test_admin_fields_match_public_copy(self):
        from src.content.models import ContactsPage

        page = ContactsPage.load()
        page.heading = 'Зв’яжіться'
        page.title_accent = 'з нами'
        page.branches_title = 'Відділення'
        page.branches_title_accent = 'по Україні'
        page.save()

        contacts_admin = self.client.get(
            reverse('admin:content_contactspage_changelist'),
            follow=True,
        )
        self.assertContains(contacts_admin, 'name="heading"')
        self.assertContains(contacts_admin, 'Заголовок блоку відділень')
        self.assertNotContains(contacts_admin, 'Вступний текст')
        self.assertNotContains(contacts_admin, 'Зображення карти')

        public = self.client.get(reverse('content:contacts'))
        self.assertContains(public, 'Зв’яжіться')
        self.assertNotContains(public, 'contacts-hero__lead')

        services_admin = self.client.get(
            reverse('admin:content_servicespage_changelist'),
            follow=True,
        )
        self.assertNotContains(services_admin, 'Вступний текст')
        faq_admin = self.client.get(
            reverse('admin:content_faqpage_changelist'),
            follow=True,
        )
        self.assertNotContains(faq_admin, 'Вступний текст')
        reviews_admin = self.client.get(
            reverse('admin:content_reviewspage_changelist'),
            follow=True,
        )
        self.assertNotContains(reviews_admin, 'Вступний текст')
        advantages_admin = self.client.get(
            reverse('admin:content_advantagespage_changelist'),
            follow=True,
        )
        self.assertNotContains(advantages_admin, 'Вступний текст')
        header_admin = self.client.get(
            reverse('admin:core_headersettings_changelist'),
            follow=True,
        )
        self.assertNotContains(header_admin, 'Текст логотипу')

    def test_legal_pages_keep_paragraphs(self):
        from src.content.models import PrivacyPage

        page = PrivacyPage.load()
        page.body = (
            '<p>Ми обробляємо персональні дані виключно для заявок. '
            'Які дані збираємо Контактні дані з форм на сайті. '
            'Навіщо Щоб підтвердити заявку.</p>'
        )
        page.save()
        public = self.client.get(reverse('content:privacy'))
        self.assertContains(public, 'legal-block__title')
        self.assertContains(public, 'Які дані збираємо')
        self.assertContains(public, 'Навіщо')
        admin = self.client.get(
            reverse('admin:content_privacypage_changelist'),
            follow=True,
        )
        self.assertContains(admin, 'textarea')
        self.assertNotContains(admin, 'tinymce')

