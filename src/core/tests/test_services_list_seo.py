import re

from django.test import TestCase
from django.urls import reverse

from src.content.models import Service, ServicesPage
from src.core.models import SiteSettings


class ServicesListPageSeoTests(TestCase):
    def setUp(self):
        self.site_name = SiteSettings.load().site_name
        self.page = ServicesPage.load()
        Service.objects.all().delete()

    def _head(self, html):
        head, _, _ = html.partition('<body')
        return head

    def _og_content(self, head, prop):
        pattern = rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"'
        match = re.search(pattern, head)
        self.assertIsNotNone(match, prop)
        return match.group(1)

    def _seed_service_leak(self):
        return Service.objects.create(
            title='Тестова послуга',
            slug='svc-leak-probe',
            short_desc='коротко',
            is_active=True,
            sort_order=0,
            seo_title='SVCLEAK',
            seo_description='SVCLEAKDESC',
        )

    def test_head_uses_services_page_seo_not_service_fields(self):
        self._seed_service_leak()
        self.page.seo_title = 'PAGETITLE'
        self.page.seo_description = 'PAGEDESC'
        self.page.save(update_fields=['seo_title', 'seo_description'])

        response = self.client.get(reverse('content:services'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        head = self._head(html)

        self.assertNotIn('SVCLEAK', html)
        self.assertNotIn('SVCLEAKDESC', html)
        self.assertIn('PAGETITLE', head)
        self.assertIn(f'<title>PAGETITLE · {self.site_name}', head)
        self.assertIn('PAGETITLE', self._og_content(head, 'og:title'))

    def test_empty_services_page_seo_falls_back_without_service_leak(self):
        self._seed_service_leak()
        self.page.seo_title = ''
        self.page.seo_description = ''
        self.page.title = 'Послуги'
        self.page.save(update_fields=['seo_title', 'seo_description', 'title'])

        response = self.client.get(reverse('content:services'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        head = self._head(html)

        self.assertNotIn('SVCLEAK', html)
        self.assertNotIn('SVCLEAKDESC', html)
        self.assertIn(f'<title>Послуги · {self.site_name}', head)
        self.assertIn('Послуги', self._og_content(head, 'og:title'))
