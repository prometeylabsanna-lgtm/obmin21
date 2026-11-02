import importlib
import json
import os

from django.apps import apps
from django.test import TestCase, override_settings

from src.content.models import AdvantagesPage, FaqPage, HomePage, ReviewsPage, Service
from src.core.deploy_seed import run_deploy_fill_pipeline
from src.core.models import SiteSettings
from src.network.branch_sync import apply_branch_catalog
from src.network.models import Branch, City


def _city_banner_payload(city):
    return {
        'banner_suffix': city.banner_suffix,
        'banner_suffix_mode': city.banner_suffix_mode,
        'banner_title': city.banner_title,
        'banner_title_mode': city.banner_title_mode,
        'banner_text': city.banner_text,
        'banner_text_mode': city.banner_text_mode,
        'banner_button': city.banner_button,
        'banner_button_mode': city.banner_button_mode,
        'seo_title': city.seo_title,
        'seo_title_mode': city.seo_title_mode,
        'seo_description': city.seo_description,
        'seo_description_mode': city.seo_description_mode,
    }


def _content_snapshot():
    home = HomePage.load()
    page = AdvantagesPage.load()
    service = Service.objects.filter(slug='obmin-valyut').first()
    city = City.objects.get(slug='lviv')
    branch = Branch.objects.get(city=city, is_active=True)
    return {
        'city': _city_banner_payload(city),
        'branch': {
            'address': branch.address,
            'phone': branch.phone,
            'hours': branch.hours,
            'map_embed_url': branch.map_embed_url,
            'lat': str(branch.lat),
            'lng': str(branch.lng),
        },
        'home': {
            'calc_lead': home.calc_lead,
            'why_empty_number': home.why_empty_number,
            'why_empty_label': home.why_empty_label,
            'seo_block_title': home.seo_block_title,
            'seo_block_body': home.seo_block_body,
            'articles_lead': home.articles_lead,
            'calc_lock': home.calc_lock,
        },
        'advantages': {
            'cmp_us_html': page.cmp_us_html,
            'stat_1_text': page.stat_1_text,
        },
        'service': None
        if service is None
        else {
            'block_text': service.block_text,
            'block_cta': service.block_cta,
        },
        'faq_intro': FaqPage.load().intro,
        'reviews_intro': ReviewsPage.load().intro,
    }


class DeployPreservesAdminEditsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        HomePage.load()
        AdvantagesPage.load()
        FaqPage.load()
        ReviewsPage.load()

    def setUp(self):
        self.city = City.objects.create(
            name='Львів',
            slug='lviv',
            sort_order=4,
            banner_suffix='',
            banner_suffix_mode='',
            banner_title='Свій заголовок',
            banner_title_mode='',
            seo_title='SEO адміна',
            seo_title_mode='',
        )
        self.branch = Branch.objects.create(
            city=self.city,
            address='вул. Степана Бандери, 35',
            phone='380991112233',
            hours='9-18',
            map_embed_url='https://www.google.com/maps/embed?pb=admin',
            is_active=True,
            sort_order=0,
        )
        home = HomePage.load()
        home.calc_lead = 'Лід адміна'
        home.why_empty_number = ''
        home.why_empty_label = ''
        home.seo_block_title = ''
        home.seo_block_body = 'Текст SEO'
        home.articles_lead = ''
        home.calc_lock = 'Свій lock'
        home.save(update_fields=[
            'calc_lead',
            'why_empty_number',
            'why_empty_label',
            'seo_block_title',
            'seo_block_body',
            'articles_lead',
            'calc_lock',
        ])
        page = AdvantagesPage.load()
        page.cmp_us_html = ''
        page.stat_1_text = 'Стат адміна'
        page.save(update_fields=['cmp_us_html', 'stat_1_text'])
        Service.objects.update_or_create(
            slug='obmin-valyut',
            defaults={
                'title': 'Обмін',
                'short_desc': 'Коротко',
                'block_text': 'Блок адміна',
                'block_points': '',
                'block_cta': '',
            },
        )
        faq = FaqPage.load()
        faq.intro = ''
        faq.save(update_fields=['intro'])
        reviews = ReviewsPage.load()
        reviews.intro = 'Відгуки адміна'
        reviews.save(update_fields=['intro'])

    def _run_deploy_paths(self):
        run_deploy_fill_pipeline(apps, None)
        run_deploy_fill_pipeline(apps, None)
        migration = importlib.import_module(
            'src.network.migrations.0015_sync_real_branches',
        )
        with override_settings(SYNC_BRANCHES_ON_MIGRATE=True):
            migration.sync_real_branches(apps, None)
        apply_branch_catalog(apps, dry_run=False)

    def test_deploy_fills_and_sync_do_not_touch_admin_state(self):
        apply_branch_catalog(apps, dry_run=False)
        before = _content_snapshot()
        self._run_deploy_paths()
        after = _content_snapshot()
        self.assertEqual(before, after)

    def test_snapshot_is_json_serializable(self):
        payload = _content_snapshot()
        json.dumps(payload, ensure_ascii=False)
