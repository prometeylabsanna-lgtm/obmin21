from django.apps import apps
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.home_copy import fill_calc_lock
from src.content.models import (
    AdvantagesPage,
    ContactsPage,
    FaqPage,
    HomePage,
    HomePromoSlide,
    HomeStat,
    ReviewsPage,
    Service,
    ServicesPage,
    VisitSteps,
)
from src.content.promo_slides import fill_promo_slides
from src.content.visit_steps import fill_home_fallback, fill_visit_steps
from src.core.models import SiteSettings


def _save(model, **values):
    row = model.load()
    for name, value in values.items():
        setattr(row, name, value)
    row.save(update_fields=list(values))
    return row


class PublicCopyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='copy-tester',
            email='copy-tester@example.com',
            password='pass-12345',
        )

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)

    def test_admin_post_shows_calc_lead_on_home(self):
        home = HomePage.load()
        token = 'ZqCalcLead'
        url = reverse('admin:content_homecalcsettings_change', args=[home.pk])
        posted = self.client.post(url, {
            'calc_kicker': home.calc_kicker,
            'calc_title': home.calc_title,
            'calc_title_accent': home.calc_title_accent,
            'calc_lead': token,
            'calc_give': home.calc_give,
            'calc_get': home.calc_get,
            'calc_rate_hint': home.calc_rate_hint,
            'calc_button': home.calc_button,
            'calc_lock': home.calc_lock,
            'calc_amount': home.calc_amount,
        }, follow=True)
        self.assertEqual(posted.status_code, 200)
        self.assertContains(self.client.get(reverse('core:home')), token)

    def test_connected_fields_reach_public_pages(self):
        service = Service.objects.create(
            title='Послуга',
            slug='probe-public',
            short_desc='коротко',
            is_active=True,
        )
        cases = (
            ('home calc kicker', 'core:home', lambda token: _save(HomePage, calc_kicker=token)),
            ('home why kicker', 'core:home', lambda token: _save(HomePage, why_kicker=token)),
            ('home services kicker', 'core:home', lambda token: _save(HomePage, services_kicker=token)),
            ('home articles kicker', 'core:home', lambda token: _save(HomePage, articles_kicker=token)),
            ('home faq kicker', 'core:home', lambda token: _save(HomePage, faq_kicker=token)),
            ('home reviews kicker', 'core:home', lambda token: _save(HomePage, reviews_kicker=token)),
            ('home reviews lead', 'core:home', lambda token: _save(HomePage, reviews_lead=token)),
            ('home seo title', 'core:home', lambda token: _save(HomePage, seo_block_title=token)),
            ('home promo title', 'core:home', lambda token: _save(HomePage, promo_title=token)),
            ('home empty stat', 'core:home', lambda token: (
                HomeStat.objects.all().delete(),
                _save(HomePage, why_empty_number=token),
            )),
            ('home map kicker', 'core:home_branch', lambda token: _save(HomePage, map_kicker=token)),
            ('reviews intro', 'reviews:review_list', lambda token: _save(ReviewsPage, intro=token)),
            ('reviews kicker', 'reviews:review_list', lambda token: _save(ReviewsPage, kicker=token)),
            ('services intro', 'content:services', lambda token: (
                _save(HomePage, articles_lead=''),
                _save(ServicesPage, intro=token),
            )),
            ('advantages intro', 'content:advantages', lambda token: _save(AdvantagesPage, intro=token)),
            ('advantages hero kicker', 'content:advantages', lambda token: _save(AdvantagesPage, hero_kicker=token)),
            ('advantages stats kicker', 'content:advantages', lambda token: _save(AdvantagesPage, stats_kicker=token)),
            ('advantages why kicker', 'content:advantages', lambda token: _save(AdvantagesPage, why_kicker=token)),
            ('advantages cmp kicker', 'content:advantages', lambda token: _save(AdvantagesPage, cmp_kicker=token)),
            ('contacts intro', 'content:contacts', lambda token: _save(ContactsPage, intro=token)),
            ('contacts branches kicker', 'content:contacts', lambda token: _save(ContactsPage, branches_kicker=token)),
            ('faq kicker', 'content:faq', lambda token: _save(FaqPage, kicker=token)),
            ('faq intro', 'content:faq', lambda token: _save(FaqPage, intro=token)),
            ('logo text', 'core:home', lambda token: _save(SiteSettings, logo_text=token, logo_accent='')),
            ('youtube', 'core:home', lambda token: _save(SiteSettings, youtube_url=f'https://probe.test/{token}')),
        )
        for name, url_name, assign in cases:
            with self.subTest(name=name):
                token = f'Zq{name.replace(" ", "")[:18]}'
                assign(token)
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, token)
        service.body = 'ZqServiceBody'
        service.seo_title = 'ZqServiceSeo'
        service.seo_description = 'ZqServiceDesc'
        service.save(update_fields=['body', 'seo_title', 'seo_description'])
        page = self.client.get(reverse('content:services'))
        html = page.content.decode()
        self.assertNotIn('ZqServiceBody', html)
        self.assertIn('alt="Послуга"', html)
        self.assertNotIn('alt="ZqServiceSeo"', html)
        head, _, body = html.partition('<body')
        self.assertIn('ZqServiceSeo', head)
        self.assertIn('ZqServiceDesc', head)
        self.assertNotIn('ZqServiceSeo', body)
        self.assertNotIn('ZqServiceDesc', body)
        self.assertIn('og:title', head)
        self.assertIn('og:description', head)

    def test_promo_slides_follow_order_and_active_flag(self):
        home = HomePage.load()
        slides = list(HomePromoSlide.objects.filter(page=home).order_by('sort_order', 'id'))
        self.assertEqual(len(slides), 4)
        later = slides[0]
        earlier = slides[1]
        later.title = 'ZqSlideLater'
        later.title_accent = ''
        later.sort_order = 9
        later.is_active = True
        later.save()
        earlier.title = 'ZqSlideEarlier'
        earlier.title_accent = ''
        earlier.sort_order = 1
        earlier.is_active = True
        earlier.save()
        if later.code == 'usd-eur':
            home.promo_title = ''
            home.promo_title_accent = ''
            home.save(update_fields=['promo_title', 'promo_title_accent'])
        if earlier.code == 'usd-eur':
            home.promo_title = ''
            home.promo_title_accent = ''
            home.save(update_fields=['promo_title', 'promo_title_accent'])
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertLess(html.find('ZqSlideEarlier'), html.find('ZqSlideLater'))
        earlier.is_active = False
        earlier.save(update_fields=['is_active'])
        hidden = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('ZqSlideEarlier', hidden)
        self.assertIn('ZqSlideLater', hidden)

    def test_visit_steps_use_rate_hold_minutes(self):
        site = SiteSettings.load()
        site.rate_hold_minutes = 45
        site.save(update_fields=['rate_hold_minutes'])
        steps = VisitSteps.load()
        expected = f'{steps.step_2_text} 45 хвилин'
        for url_name in ('content:services', 'content:advantages'):
            html = self.client.get(reverse(url_name)).content.decode()
            self.assertIn(expected, html)
            self.assertNotIn('курс діє 30', html.casefold())

    def test_public_fills_are_idempotent(self):
        home = HomePage.load()
        home.why_empty_number = '9K'
        home.why_empty_label = 'Свій підпис'
        home.calc_lock = 'Свій рядок'
        home.save(update_fields=['why_empty_number', 'why_empty_label', 'calc_lock'])
        slide = HomePromoSlide.objects.get(page=home, code='crypto')
        slide.title = 'Свій слайд'
        slide.save(update_fields=['title'])
        steps = VisitSteps.load()
        steps.step_1_title = 'Свій крок'
        steps.save(update_fields=['step_1_title'])

        def run():
            fill_promo_slides(apps, None)
            fill_visit_steps(apps, None)
            fill_home_fallback(apps, None)
            fill_calc_lock(apps, None)

        run()
        run()
        home.refresh_from_db()
        slide.refresh_from_db()
        steps.refresh_from_db()
        self.assertEqual(home.why_empty_number, '9K')
        self.assertEqual(home.why_empty_label, 'Свій підпис')
        self.assertEqual(home.calc_lock, 'Свій рядок')
        self.assertEqual(slide.title, 'Свій слайд')
        self.assertEqual(steps.step_1_title, 'Свій крок')
        self.assertEqual(HomePromoSlide.objects.filter(page=home, code='crypto').count(), 1)

        HomePage.objects.filter(pk=home.pk).update(
            why_empty_number='',
            why_empty_text='   ',
            calc_lock='Курс діє 30 хв',
        )
        VisitSteps.objects.filter(pk=steps.pk).update(step_1_title='')
        run()
        home.refresh_from_db()
        steps.refresh_from_db()
        self.assertEqual(home.why_empty_number, '7K')
        self.assertTrue(home.why_empty_text.strip())
        self.assertEqual(home.calc_lock, 'Курс діє')
        self.assertEqual(steps.step_1_title, 'Оберіть послугу')
        number = home.why_empty_number
        lock = home.calc_lock
        title = steps.step_1_title
        run()
        home.refresh_from_db()
        steps.refresh_from_db()
        self.assertEqual(home.why_empty_number, number)
        self.assertEqual(home.calc_lock, lock)
        self.assertEqual(steps.step_1_title, title)

    def test_first_slide_keeps_template_title(self):
        home = HomePage.load()
        home.promo_title = 'Вигідний курс'
        home.save(update_fields=['promo_title'])
        fill_promo_slides(apps, None)
        home.refresh_from_db()
        self.assertEqual(home.promo_title, 'Вигідний курс на')
        slide = HomePromoSlide.objects.get(page=home, code='usd-eur')
        self.assertEqual(slide.title, 'Вигідний курс на')
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('Вигідний курс на', html)
        self.assertNotIn('Вигідний курс на на', html)

    def test_empty_kickers_and_seo_block_stay_off_home(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('id="about"', html)
        self.assertNotIn('calc-head__lead', html)

    def test_sidebar_lists_slide_and_steps_blocks(self):
        page = self.client.get(reverse('admin:index'))
        self.assertContains(page, 'Слайди вигідного курсу')
        self.assertContains(page, 'Три кроки')
        self.assertContains(page, reverse('admin:content_homepromoslide_changelist'))
        self.assertContains(page, reverse('admin:content_visitsteps_changelist'))
