from django.test import TestCase, override_settings
from django.urls import reverse

CREDIT_URL = 'https://www.prometeylabs.com/corporate-website-v2/'


class FooterDeveloperLinkTests(TestCase):
    def test_home_has_nofollow_credit_link(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, CREDIT_URL)
        self.assertContains(response, 'nofollow')
        self.assertContains(response, '>PrometeyLabs</a>')

    def test_inner_pages_show_credit_without_link(self):
        for url in (
            reverse('content:privacy'),
            reverse('content:contacts'),
            reverse('content:offer'),
        ):
            response = self.client.get(url)
            self.assertContains(response, 'PrometeyLabs')
            self.assertNotContains(response, CREDIT_URL)
            self.assertNotContains(response, 'site-footer__credit-link')

    @override_settings(DEBUG=False)
    def test_404_footer_has_no_agency_link(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'PrometeyLabs', status_code=404)
        self.assertNotContains(response, CREDIT_URL, status_code=404)
        self.assertNotContains(response, 'site-footer__credit-link', status_code=404)
