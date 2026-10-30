from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from src.content.models import CitiesPage, HomePage
from src.core.models import SiteSettings
from src.network.models import Branch, City


class BranchListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        CitiesPage.load()
        page = HomePage.load()
        page.show_map = True
        page.save(update_fields=['show_map'])
        cls.kyiv = City.objects.create(
            name='Київ', slug='kyiv-list', phone='+380441112233', sort_order=0,
        )
        cls.kharkiv = City.objects.create(
            name='Харків', slug='kharkiv-list', phone='+380991112233', sort_order=1,
        )
        cls.kyiv_branch = Branch.objects.create(
            city=cls.kyiv,
            address='вул. Бульварно-Кудрявська, 32',
            sort_order=0,
        )
        cls.first = Branch.objects.create(
            city=cls.kharkiv,
            address='вул. Кацарська, 36/38',
            sort_order=0,
        )
        cls.second = Branch.objects.create(
            city=cls.kharkiv,
            name='Барабашово',
            address='метро Академіка Барабашова',
            sort_order=1,
        )

    def test_lists_show_both_kharkiv_branches_in_order(self):
        home = self.client.get(reverse('core:home')).content.decode()
        cities = self.client.get(reverse('network:city_list'))
        cities_html = cities.content.decode()
        for html in (home, cities_html):
            self.assertIn('Харків «Барабашово»', html)
            first = html.find('Харків')
            second = html.find('Харків «Барабашово»')
            self.assertGreaterEqual(first, 0)
            self.assertGreater(second, first)
        self.assertGreaterEqual(home.count('name="branch"'), 3)
        self.assertContains(cities, 'вул. Кацарська, 36/38')
        self.assertContains(cities, 'метро Академіка Барабашова')

    def test_set_city_keeps_selected_kharkiv_branch(self):
        switched = self.client.post(
            reverse('network:set_city'),
            {'city': self.kharkiv.slug, 'branch': str(self.second.pk)},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(self.client.session['city_slug'], self.kharkiv.slug)
        self.assertEqual(self.client.session['branch_id'], self.second.pk)
        self.assertEqual(
            self.client.cookies[settings.BRANCH_COOKIE_NAME].value,
            str(self.second.pk),
        )
        self.assertContains(switched, 'Харків «Барабашово»')

        fragment = self.client.get(reverse('core:home_branch'))
        self.assertContains(fragment, 'метро Академіка Барабашова')
        self.assertNotContains(fragment, 'вул. Кацарська, 36/38')
        self.assertContains(fragment, 'Харків «Барабашово»')
