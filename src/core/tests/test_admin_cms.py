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
            username='tester',
            email='tester@example.com',
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
        self.assertContains(resp, 'Колір акценту шапки')
        self.assertContains(resp, 'Колір підсвітки шапки')

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
            'color_bg': '#f3f6fb',
            'color_text': '#052145',
            'color_accent': '#ca8d42',
            'color_highlight': '#b87b2c',
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
        self.assertContains(resp, reverse('admin:content_faqpage_changelist'))
        self.assertContains(resp, reverse('admin:content_faqitem_changelist'))
        self.assertContains(resp, reverse('admin:content_reviewspage_changelist'))
        self.assertContains(resp, reverse('admin:reviews_review_changelist'))
        self.assertContains(resp, 'Питання і відповіді')
        self.assertContains(resp, reverse('admin:network_city_changelist'))
        self.assertContains(resp, reverse('admin:network_contactcity_changelist'))
        html = resp.content.decode()
        self.assertIn('Сторінка Блог', html)
        self.assertNotIn('Інші сторінки', html)
        self.assertNotIn('Міста мережі', html)
        self.assertIn('Адреси відділень', html)
        faq_pos = html.find('Питання і відповіді')
        contacts_pos = html.find('>Контакти<')
        if contacts_pos == -1:
            contacts_pos = html.find('Контакти')
        self.assertNotEqual(faq_pos, -1)
        self.assertLess(faq_pos, contacts_pos)
        self.assertNotIn('Заголовок сторінки', html)
        self.assertLess(
            html.find('/admin/content/blogpage/'),
            html.find('/admin/blog/post/'),
        )
        self.assertContains(resp, 'Оформлення')
        self.assertContains(resp, reverse('admin:content_homesearchsettings_changelist'))

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
        self.assertNotContains(reviews_admin, 'Підзаголовок')
        advantages_admin = self.client.get(
            reverse('admin:content_advantagespage_changelist'),
            follow=True,
        )
        self.assertNotContains(advantages_admin, 'Вступний текст')
        self.assertContains(advantages_admin, 'Чому обирають Обмін21')
        self.assertContains(advantages_admin, 'Обмін21 у цифрах')
        self.assertContains(advantages_admin, 'Чому люди обирають обмінювати в Обмін21')
        self.assertContains(advantages_admin, 'Обмін21 чи звичайний обмінник')
        self.assertContains(advantages_admin, 'Список «Рекомендуємо»')
        self.assertContains(advantages_admin, 'tinymce')
        self.assertContains(advantages_admin, 'Фото банера')
        self.assertContains(advantages_admin, 'Картинка монет')
        self.assertContains(advantages_admin, 'Сторінка переваг')
        self.assertContains(advantages_admin, 'cms-seg-tabs')
        self.assertContains(advantages_admin, 'images/coins.png')
        self.assertContains(advantages_admin, 'li span::after')
        header_admin = self.client.get(
            reverse('admin:core_headersettings_changelist'),
            follow=True,
        )
        self.assertNotContains(header_admin, 'Текст логотипу')
        self.assertNotContains(header_admin, 'Посилання Telegram')
        self.assertNotContains(header_admin, 'якщо місто не обрано')
        footer_admin = self.client.get(
            reverse('admin:core_footersettings_changelist'),
            follow=True,
        )
        self.assertNotContains(footer_admin, 'Посилання Telegram')
        self.assertNotContains(footer_admin, 'Посилання Instagram')
        self.assertNotContains(footer_admin, 'якщо місто не обрано')
        settings_admin = self.client.get(
            reverse('admin:core_sitesettings_changelist'),
            follow=True,
        )
        self.assertContains(settings_admin, 'Посилання Telegram')
        self.assertContains(settings_admin, 'Посилання Instagram')
        self.assertNotContains(settings_admin, 'якщо місто не обрано')

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

    def test_short_copy_skips_tinymce(self):
        from src.content.models import Service

        svc = Service.objects.create(
            title='Тестова картка',
            slug='testova-kartka-short',
            short_desc='Короткий текст без редактора',
        )
        page = self.client.get(
            reverse('admin:content_service_change', args=[svc.pk]),
        )
        body = page.content.decode()
        self.assertContains(page, 'Короткий опис')
        self.assertRegex(body, r'<textarea[^>]*name="short_desc"')
        self.assertNotRegex(
            body,
            r'<textarea[^>]*name="short_desc"[^>]*class="[^"]*tinymce',
        )
        self.assertIn('data-mce-conf', body)
        self.assertIn('name="body"', body)

    def test_home_articles_use_checkboxes(self):
        page = self.client.get(
            reverse('admin:content_homearticlessettings_change', args=[1]),
        )
        self.assertContains(page, 'Показувати блок на головній')
        self.assertContains(page, 'Статті беруться з розділу Блог')
        self.assertNotContains(page, 'cms-check-list')
        self.assertNotContains(page, 'Позначте статті')

    def test_reviews_page_renders_html(self):
        from django.utils import timezone
        from src.reviews.models import Review

        Review.objects.create(
            name='Олена',
            city_name='Київ',
            text='<p>Швидкий обмін</p>',
            is_published=True,
            published_at=timezone.now(),
        )
        resp = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Швидкий обмін')
        self.assertNotContains(resp, 'Invalid filter')

    def test_map_city_has_no_branches(self):
        from src.network.models import Branch, City

        city = City.objects.filter(is_active=True).first()
        if city is None:
            city = City.objects.create(name='Київ', slug='kyiv-test')
        Branch.objects.get_or_create(
            city=city,
            address='вул. Хрещатик, 1',
            defaults={'hours': '09:00–18:00', 'phone': '+380'},
        )
        page = self.client.get(
            reverse('admin:network_mapcity_change', args=[city.pk]),
        )
        self.assertNotContains(page, 'name="branches-0-address"')
        contacts = self.client.get(
            reverse('admin:network_contactcity_change', args=[city.pk]),
        )
        self.assertContains(contacts, 'data-inline-type="stacked"')
        self.assertContains(contacts, 'name="branches-0-address"')
        self.assertContains(contacts, 'Графік')
        self.assertContains(contacts, 'Адреса')
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse('admin:network_branch_changelist')
        index = self.client.get(reverse('admin:index'))
        self.assertContains(index, 'Картки послуг')
        self.assertContains(index, reverse('admin:content_service_changelist'))

    def test_rates_page_admin_explains_public_url(self):
        page = self.client.get(
            reverse('admin:content_ratespage_changelist'),
            follow=True,
        )
        self.assertContains(page, '/kursy/')
        self.assertContains(page, 'Всі валюти')
        self.assertContains(page, 'Основна інформація')
        self.assertContains(page, 'Валютні пари')
        self.assertContains(page, 'Таблиця курсів')
        self.assertNotContains(page, 'tinymce')
        public = self.client.get(reverse('rates:rates_page'))
        self.assertEqual(public.status_code, 200)
        self.assertContains(public, 'rates-page-card')
        self.assertNotContains(public, 'calc-box')
        self.assertNotContains(public, 'reviews-section')

    def test_currency_pair_shows_default_flag(self):
        from src.rates.models import CurrencyPair

        pair = CurrencyPair.objects.create(
            code='USD/UAH',
            name='Долар США',
            slug='usd-uah',
            base_code='UAH',
        )
        page = self.client.get(
            reverse('admin:rates_currencypair_change', args=[pair.pk]),
        )
        self.assertContains(page, 'cms-flag')
        self.assertContains(page, 'data-code="USD"')

    def test_quote_changelist_splits_cash_and_crypto(self):
        from src.rates.models import CurrencyPair, Quote, RateBoard

        pair = CurrencyPair.objects.create(
            code='USD/UAH',
            name='Долар США',
            slug='usd-uah-admin',
            base_code='UAH',
        )
        Quote.objects.create(
            pair=pair,
            board=RateBoard.RETAIL,
            buy='41.20',
            sell='41.65',
        )
        Quote.objects.create(
            pair=pair,
            board=RateBoard.CRYPTO,
            buy='41.10',
            sell='41.50',
        )
        cash = self.client.get(reverse('admin:rates_quote_changelist'))
        self.assertContains(cash, 'cms-board-tabs')
        self.assertContains(cash, 'Готівка')
        self.assertContains(cash, 'Крипто')
        self.assertContains(cash, 'Обрати дію')
        self.assertNotContains(cash, 'Select action')
        self.assertNotContains(cash, 'Опт')
        self.assertNotContains(cash, 'Крос')
        self.assertContains(cash, '41.20')
        self.assertNotContains(cash, '41.10')
        crypto = self.client.get(
            reverse('admin:rates_quote_changelist') + '?board=crypto',
        )
        self.assertContains(crypto, '41.10')
        self.assertNotContains(crypto, '41.20')
        look = self.client.get(
            reverse('admin:content_homesearchsettings_changelist'),
            follow=True,
        )
        self.assertContains(look, 'Колір акценту')
        self.assertContains(look, 'Колір підсвітки')
        self.assertNotContains(look, 'Назва для SEO')
        self.assertNotContains(look, 'Показувати блок на головній')

    def test_service_cards_show_site_image(self):
        from src.content.models import Service

        svc = Service.objects.create(
            title='Грошові перекази по Україні',
            slug='groshovi-perekazy',
            short_desc='Текст',
        )
        listing = self.client.get(reverse('admin:content_service_changelist'))
        self.assertContains(listing, 'cms-svc-thumb')
        self.assertContains(listing, 'images/services/groshovi-perekazy.jpg')
        page = self.client.get(
            reverse('admin:content_service_change', args=[svc.pk]),
        )
        self.assertContains(page, 'cms-image')
        self.assertContains(page, 'images/services/groshovi-perekazy.jpg')
        self.assertContains(page, 'data-cms-image-preview')

