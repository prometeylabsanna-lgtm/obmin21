from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import Client, TestCase
from django.urls import reverse


class TinyMCERouteTests(TestCase):
    disabled_paths = (
        '/tinymce/filebrowser/',
        '/tinymce/flatpages_link_list/',
    )

    def test_filebrowser_and_flatpages_404_for_anonymous_and_staff(self):
        staff = User.objects.create_user(
            username='tinymce-staff',
            password='pass-12345',
            is_staff=True,
        )
        staff_client = Client()
        staff_client.force_login(staff)
        for client in (Client(), staff_client):
            for path in self.disabled_paths:
                response = client.get(path)
                self.assertEqual(response.status_code, 404, path)

    def test_faq_add_form_loads_tinymce(self):
        admin = User.objects.create_superuser(
            username='tinymce-admin',
            email='tinymce-admin@example.com',
            password='pass-12345',
        )
        self.client.force_login(admin)
        response = self.client.get(reverse('admin:content_faqitem_add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tinymce')
        self.assertContains(response, 'data-mce-conf')
        self.assertNotContains(response, 'flatpages_link_list')
        self.assertNotContains(response, '/tinymce/filebrowser/')
        self.assertNotIn('link_list', settings.TINYMCE_DEFAULT_CONFIG)
        self.assertFalse(settings.TINYMCE_FILEBROWSER)

        if getattr(settings, 'TINYMCE_COMPRESSOR', False):
            asset_url = reverse('tinymce-compressor')
            self.assertContains(response, asset_url)
            asset = self.client.get(asset_url)
            self.assertEqual(asset.status_code, 200, asset_url)
        else:
            asset_url = static('tinymce/tinymce.min.js')
            self.assertContains(response, asset_url)
            self.assertTrue(finders.find('tinymce/tinymce.min.js'))
            init_url = static('django_tinymce/init_tinymce.js')
            self.assertContains(response, init_url)
            self.assertTrue(finders.find('django_tinymce/init_tinymce.js'))

    def test_compressor_route_still_works(self):
        url = reverse('tinymce-compressor')
        self.assertEqual(url, '/tinymce/compressor/')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response['Content-Type'])
