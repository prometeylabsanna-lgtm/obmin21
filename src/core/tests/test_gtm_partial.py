from django.test import TestCase, override_settings
from django.urls import reverse


class GtmPartialTests(TestCase):
    @override_settings(GTM_ID='')
    def test_nothing_rendered_without_id(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('gtm-consent.js', html)
        self.assertNotIn('googletagmanager', html)

    @override_settings(GTM_ID='GTM-TEST123')
    def test_consent_script_rendered_with_id(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('data-gtm-id="GTM-TEST123"', html)
        self.assertIn('ns.html?id=GTM-TEST123', html)

    @override_settings(GTM_ID='bad"><script>')
    def test_invalid_id_ignored(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('gtm-consent.js', html)
