from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.network.admin import BannerCityAdmin
from src.network.cms_proxies import BannerCity
from src.network.models import City


class BannerSuffixBlankTests(TestCase):
    def test_field_allows_empty(self):
        field = City._meta.get_field('banner_suffix')
        self.assertTrue(field.blank)
        city = City(name='Київ', slug='kyiv-suffix', banner_suffix='')
        city.full_clean()
        city.save()
        self.assertEqual(City.objects.get(pk=city.pk).banner_suffix, '')

    def test_banner_admin_saves_empty_suffix(self):
        city = City.objects.create(name='Київ', slug='kyiv-banner-empty')
        user = User.objects.create_superuser('admin', 'a@b.c', 'x')
        request = RequestFactory().post('/admin/')
        request.user = user
        admin = BannerCityAdmin(BannerCity, None)
        form_class = admin.get_form(request, city)
        form = form_class(
            data={
                'banner_title': city.banner_title,
                'banner_title_mode': '',
                'banner_suffix': '',
                'banner_suffix_mode': '',
                'banner_text': city.banner_text,
                'banner_text_mode': '',
                'banner_button': city.banner_button,
                'banner_button_mode': '',
            },
            instance=city,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        city.refresh_from_db()
        self.assertEqual(city.banner_suffix, '')

    def test_home_h1_omits_empty_suffix(self):
        SiteSettings.load()
        HomePage.load()
        city = City.objects.create(
            name='Київ',
            slug='kyiv-home-suffix',
            phone='+380441112233',
            banner_suffix='',
        )
        self.client.post(reverse('network:set_city'), {'city': city.slug})
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('<span data-hero-suffix></span>', html)
