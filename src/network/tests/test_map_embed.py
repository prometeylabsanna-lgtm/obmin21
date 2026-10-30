from decimal import Decimal
from urllib.parse import quote_plus

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from src.core.admin_city import BranchInline
from src.network.cms_proxies import ContactCity, MapCity
from src.network.models import MAP_EMBED_HELP, Branch, City, validate_map_embed_url

MAP_FIELDS = ('map_embed_url', 'map_url', 'lat', 'lng')

ALLOWED_EMBED_URLS = (
    '',
    'https://www.google.com/maps/embed?pb=!1m18!1m12',
    'https://google.com/maps',
    'https://google.com/maps/',
    'https://google.com/maps/place/Kyiv',
    'https://www.google.com/maps/embed?pb=abc#map',
    'https://maps.google.com/maps?q=Kyiv&z=15&hl=uk&output=embed',
    'https://maps.google.com/',
    'https://maps.google.com',
    'https://WWW.Google.com/maps/embed?pb=1',
    'https://www.google.com/Maps/embed?pb=1',
    'https://maps.google.com:443/maps?q=1',
    'https://www.google.com/maps/place/Kyiv/@50.45,30.52,17z',
)

REJECTED_EMBED_URLS = (
    'http://www.google.com/maps/embed?pb=1',
    'http://maps.google.com/maps',
    'http://google.com/maps',
    'https://evil.com/maps',
    'https://google.com.evil.com/maps',
    'https://www.google.com.evil.com/maps/embed',
    'https://maps.google.com.evil.com/',
    'https://maps.google.com.evil.com/maps',
    'https://notgoogle.com/maps',
    'javascript:alert(1)',
    'javascript:https://www.google.com/maps',
    'https://www.google.com/search?q=maps',
    'https://www.google.com/',
    'https://google.com/',
    'https://google.com/search',
    'https://evil.google.com/maps',
    'https://foo.maps.google.com/',
    'ftp://maps.google.com/maps',
    '//www.google.com/maps',
    'https://www.google.com@evil.com/maps',
    'data:text/html,hi',
)


def _embed(query):
    return (
        'https://maps.google.com/maps?q='
        + quote_plus(query)
        + '&z=15&hl=uk&output=embed'
    )


class BranchMapEmbedTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Тест', slug='map-embed')

    def branch(self, **kwargs):
        data = {'city': self.city, 'address': 'вул. Тестова, 5'}
        data.update(kwargs)
        return Branch(**data)

    def test_embed_url_wins_over_coords_and_address(self):
        embed = 'https://www.google.com/maps/embed?pb=branch-test'
        branch = self.branch(
            map_embed_url=embed,
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertEqual(branch.map_embed_src(), embed)

    def test_coords_used_when_embed_url_empty(self):
        branch = self.branch(
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        expected = _embed('50.450100,30.523400')
        self.assertEqual(
            branch.map_embed_src(),
            'https://maps.google.com/maps?q=50.450100%2C30.523400&z=15&hl=uk&output=embed',
        )
        self.assertEqual(branch.map_embed_src(), expected)
        blank = self.branch(
            map_embed_url='   ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertEqual(blank.map_embed_src(), expected)
        zero = self.branch(lat=Decimal('0'), lng=Decimal('0'))
        self.assertEqual(zero.map_embed_src(), _embed('0,0'))

    def test_address_used_without_embed_or_coords(self):
        branch = self.branch()
        self.assertEqual(
            branch.map_embed_src(),
            _embed('вул. Тестова, 5, Ukraine'),
        )

    def test_lat_only_falls_back_to_address(self):
        branch = self.branch(lat=Decimal('50.450100'))
        self.assertIsNone(branch.lng)
        self.assertEqual(
            branch.map_embed_src(),
            _embed('вул. Тестова, 5, Ukraine'),
        )

    def test_coords_used_only_with_real_address(self):
        other = City.objects.create(name='Полтава', slug='poltava-map')
        stub = Branch(
            city=other,
            address='вул. Хрещатик, 1, Київ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertFalse(stub.has_real_address)
        self.assertEqual(
            stub.map_embed_src(),
            _embed('вул. Хрещатик, 1, Київ, Ukraine'),
        )
        spaced = Branch(
            city=other,
            address='вул.\u00a0Хрещатик,  1, Київ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertFalse(spaced.has_real_address)
        self.assertEqual(
            spaced.map_embed_src(),
            _embed('вул.\u00a0Хрещатик,  1, Київ, Ukraine'),
        )
        kyiv = City.objects.create(name='Київ', slug='kyiv')
        capital = Branch(
            city=kyiv,
            address='вул. Хрещатик, 1, Київ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertTrue(capital.has_real_address)
        self.assertEqual(capital.map_embed_src(), _embed('50.450100,30.523400'))
        blank = self.branch(
            address='   ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
        )
        self.assertFalse(blank.has_real_address)
        self.assertEqual(blank.map_embed_src(), '')

    def test_help_text_and_blank_field(self):
        field = Branch._meta.get_field('map_embed_url')
        self.assertTrue(field.blank)
        self.assertFalse(field.null)
        self.assertIn('Google Maps → Поділитися → Вбудувати карту', field.help_text)
        self.assertIn('скопіювати значення src з коду iframe', field.help_text)
        self.assertEqual(field.help_text, MAP_EMBED_HELP)

    def test_allowed_urls_pass_clean_and_validator(self):
        for url in ALLOWED_EMBED_URLS:
            validate_map_embed_url(url)
            branch = self.branch(map_embed_url=url)
            branch.full_clean()

    def test_rejected_urls_fail_clean_and_validator(self):
        for url in REJECTED_EMBED_URLS:
            with self.assertRaises(ValidationError):
                validate_map_embed_url(url)
            branch = self.branch(map_embed_url=url)
            with self.assertRaises(ValidationError) as ctx:
                branch.full_clean()
            self.assertIn('map_embed_url', ctx.exception.message_dict)

    def test_lookalike_error_is_on_the_field(self):
        branch = self.branch(map_embed_url='https://google.com.evil.com/maps')
        with self.assertRaises(ValidationError) as ctx:
            branch.full_clean()
        self.assertEqual(len(ctx.exception.message_dict['map_embed_url']), 1)

    def test_padded_embed_url_is_stripped(self):
        url = 'https://maps.google.com/maps?q=1&output=embed'
        branch = self.branch(map_embed_url=f'  {url}  ')
        branch.full_clean()
        self.assertEqual(branch.map_embed_url, url)
        self.assertEqual(branch.map_embed_src(), url)


class BranchMapAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='map-admin',
            email='map-admin@example.com',
            password='pass-12345',
        )
        cls.city = City.objects.create(name='Адмін', slug='map-admin-city')
        Branch.objects.create(city=cls.city, address='вул. Тестова, 5')

    def setUp(self):
        self.client.force_login(self.user)

    def test_branch_editors_show_map_fields(self):
        for name in MAP_FIELDS:
            self.assertIn(name, BranchInline.fields)
        editors = []
        for model, model_admin in admin.site._registry.items():
            if model is Branch:
                shown = _admin_field_names(model_admin)
                for name in MAP_FIELDS:
                    self.assertIn(name, shown)
                editors.append(model)
            for inline in getattr(model_admin, 'inlines', ()):
                if getattr(inline, 'model', None) is not Branch:
                    continue
                editors.append(model)
                if inline.fields is not None:
                    for name in MAP_FIELDS:
                        self.assertIn(name, inline.fields)
        self.assertIn(ContactCity, editors)
        self.assertNotIn(MapCity, editors)
        page = self.client.get(
            reverse('admin:network_contactcity_change', args=[self.city.pk]),
        )
        self.assertEqual(page.status_code, 200)
        for name in MAP_FIELDS:
            self.assertContains(page, f'name="branches-0-{name}"')
        self.assertContains(page, 'Поділитися')
        self.assertContains(page, 'Вбудувати карту')
        self.assertContains(page, 'скопіювати значення src')
        self.assertContains(page, 'Широта')
        self.assertContains(page, 'Довгота')
        self.assertContains(page, 'Посилання на карту')
        self.assertIn(Branch, admin.site._registry)
        changelist = self.client.get(reverse('admin:network_branch_changelist'))
        self.assertEqual(changelist.status_code, 200)
        branch_admin = self.client.get(
            reverse('admin:network_branch_change', args=[self.city.branches.get().pk]),
        )
        self.assertEqual(branch_admin.status_code, 200)
        for name in MAP_FIELDS:
            self.assertContains(branch_admin, f'name="{name}"')


def _admin_field_names(model_admin):
    names = []
    if model_admin.fields:
        names.extend(model_admin.fields)
    for _title, opts in model_admin.fieldsets or ():
        names.extend(opts.get('fields') or ())
    return names
