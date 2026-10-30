from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from django.conf import settings

from src.core.admin_city import BranchInline
from src.network.cms_proxies import ContactCity
from src.network.geocoding import GEOCODE_FAILURE, GEOCODE_SUCCESS
from src.network.models import Branch, City


def _request(user):
    request = RequestFactory().post('/branch-save')
    request.user = user
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    MessageMiddleware(lambda req: None).process_request(request)
    return request


def _texts(request):
    return [str(item) for item in get_messages(request)]


def _data_from_form(form):
    data = {}
    for name, field in form.fields.items():
        key = form.add_prefix(name) if form.prefix else name
        value = form[name].value()
        if isinstance(value, bool):
            if value:
                data[key] = 'on'
            continue
        if value is None:
            data[key] = ''
            continue
        rendered = field.widget.format_value(value)
        data[key] = '' if rendered is None else str(rendered)
    return data


def _management_data(formset):
    data = {}
    form = formset.management_form
    for name, field in form.fields.items():
        value = form[name].value()
        rendered = field.widget.format_value(value)
        data[form.add_prefix(name)] = '' if rendered is None else str(rendered)
    return data


class _House:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append((request, timeout))
        query = parse_qs(urlparse(request.full_url).query).get('q', [''])[0]
        body = self.payload
        if 'Неіснуюча' in query:
            body = []
        raw = __import__('json').dumps(body).encode()

        class _Body:
            def read(self, limit=-1):
                return raw if limit is None or limit < 0 else raw[:limit]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Body()


class BranchAdminCoordinateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='branch-coords',
            email='branch-coords@example.com',
            password='pass-12345',
        )
        self.client.force_login(self.user)
        self.city = City.objects.create(name='Львів', slug='lviv-admin')
        self.model_admin = admin.site._registry[Branch]
        self.request = _request(self.user)
        self.house = [{
            'lat': '49.841900',
            'lon': '24.031500',
            'addresstype': 'building',
            'type': 'house',
            'address': {'house_number': '8'},
        }]

    def _branch(self, **kwargs):
        data = {
            'city': self.city,
            'address': 'вул. Стара, 1, Львів',
            'hours': 'старий',
        }
        data.update(kwargs)
        return Branch.objects.create(**data)

    def _form(self, branch, **overrides):
        form_class = self.model_admin.get_form(self.request, branch)
        data = _data_from_form(form_class(instance=branch))
        data.update(overrides)
        form = form_class(data, instance=branch)
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def _save(self, branch, opener, **overrides):
        form = self._form(branch, **overrides)
        with patch('src.network.geocoding.urlopen', opener):
            self.model_admin.save_model(self.request, form.instance, form, True)
        form.instance.refresh_from_db()
        return form.instance

    def test_address_change_geocodes_and_failure_clears_coords(self):
        branch = self._branch(lat=Decimal('49.000000'), lng=Decimal('24.000000'))
        opener = _House(self.house)
        saved = self._save(branch, opener, address='вул. Нова, 8, Львів')
        self.assertEqual(saved.lat, Decimal('49.841900'))
        self.assertEqual(saved.lng, Decimal('24.031500'))
        self.assertFalse(saved.coords_manual)
        self.assertEqual(_texts(self.request), [GEOCODE_SUCCESS])
        self.assertEqual(len(opener.calls), 1)

        missed = _House([])
        self.request = _request(self.user)
        saved = self._save(saved, missed, address='вул. Неіснуюча, 9, Львів')
        self.assertIsNone(saved.lat)
        self.assertIsNone(saved.lng)
        self.assertFalse(saved.coords_manual)
        self.assertEqual(_texts(self.request), [GEOCODE_FAILURE])

    def test_manual_coords_flag_still_blocks_address_geocode(self):
        branch = self._branch(
            lat=Decimal('49.200000'),
            lng=Decimal('24.100000'),
            coords_manual=True,
        )
        opener = _House(self.house)
        saved = self._save(branch, opener, address='вул. Інша, 2, Львів')
        self.assertEqual(saved.lat, Decimal('49.200000'))
        self.assertEqual(saved.lng, Decimal('24.100000'))
        self.assertTrue(saved.coords_manual)
        self.assertEqual(opener.calls, [])
        self.assertEqual(_texts(self.request), [])

    def test_stub_address_change_clears_coords_without_http(self):
        other = City.objects.create(name='Полтава', slug='poltava-admin')
        branch = self._branch(
            city=other,
            address='вул. Справжня, 1, Полтава',
            lat=Decimal('49.500000'),
            lng=Decimal('34.500000'),
        )
        opener = _House(self.house)
        saved = self._save(branch, opener, address='вул. Хрещатик, 1, Київ')
        self.assertFalse(saved.has_real_address)
        self.assertIsNone(saved.lat)
        self.assertIsNone(saved.lng)
        self.assertEqual(opener.calls, [])
        self.assertEqual(_texts(self.request), [])

    def test_new_branch_is_geocoded(self):
        form_class = self.model_admin.get_form(self.request, None)
        data = _data_from_form(form_class())
        data.update({
            'city': str(self.city.pk),
            'address': 'вул. Нова, 8, Львів',
            'sort_order': '0',
        })
        form = form_class(data)
        self.assertTrue(form.is_valid(), form.errors)
        opener = _House(self.house)
        with patch('src.network.geocoding.urlopen', opener):
            self.model_admin.save_model(self.request, form.instance, form, False)
        form.instance.refresh_from_db()
        self.assertEqual(form.instance.lat, Decimal('49.841900'))
        self.assertFalse(form.instance.coords_manual)
        self.assertEqual(_texts(self.request), [GEOCODE_SUCCESS])

    def test_inline_address_change_geocodes(self):
        branch = self._branch()
        inline = BranchInline(ContactCity, admin.site)
        request = _request(self.user)
        FormSet = inline.get_formset(request, self.city)
        unbound = FormSet(instance=self.city)
        data = _management_data(unbound)
        for form in unbound.forms:
            data.update(_data_from_form(form))
        prefix = unbound.prefix
        data[f'{prefix}-0-address'] = 'вул. Нова, 8, Львів'
        bound = FormSet(data=data, instance=self.city)
        self.assertTrue(bound.is_valid(), bound.errors)
        opener = _House(self.house)
        with patch('src.network.geocoding.urlopen', opener):
            bound.save()
        branch.refresh_from_db()
        self.assertEqual(branch.address, 'вул. Нова, 8, Львів')
        self.assertEqual(branch.lat, Decimal('49.841900'))
        self.assertEqual(branch.lng, Decimal('24.031500'))
        self.assertFalse(branch.coords_manual)
        self.assertEqual(_texts(request), [GEOCODE_SUCCESS])

    def test_hours_field_is_editable_without_day_rows(self):
        branch = self._branch(hours='Пн–Нд, 8:00–21:00')
        form = self._form(branch)
        self.assertIn('hours', form.fields)
        self.assertNotIn('hours', self.model_admin.readonly_fields)
        self.assertNotIn('coords_manual', getattr(self.model_admin, 'fields', ()) or ())
        self.assertFalse(self.model_admin.inlines)
        self.assertEqual(branch.hours_display, 'Пн–Нд, 8:00–21:00')

    def test_admin_hides_coords_and_route_fields(self):
        self.assertNotIn('geocode_coordinates', self.model_admin.actions)
        for name in ('map_url', 'lat', 'lng', 'coords_manual'):
            self.assertNotIn(name, self.model_admin.fields)
            self.assertNotIn(name, BranchInline.fields)

    def test_client_instructions(self):
        text = (
            settings.BASE_DIR / 'docs' / 'client_branch_instructions_uk.md'
        ).read_text(encoding='utf-8')
        token = str(getattr(settings, 'ADMIN_URL', '') or '')
        self.assertFalse(bool(token) and token in text)
        bare = token.strip('/')
        self.assertFalse(bool(bare) and bare in text)
        section = Branch._meta.verbose_name_plural
        self.assertIn(f'«{section}»', text)
        self.assertIn('адмін-панелі відкрийте розділ «Відділення»', text)
        self.assertNotIn('Широта', text)
        self.assertNotIn('Довгота', text)
        self.assertIn('Графік роботи', text)
        self.assertIn('URL вбудованої карти', text)
        self.assertNotIn('Вихідний', text)
        self.assertNotIn('coords_manual', text)
        self.assertNotIn('Nominatim', text)
        self.assertNotIn('jsonv2', text)
        page = self.client.get(reverse('admin:network_branch_changelist'))
        self.assertNotContains(page, 'Визначити координати')
        branch = self._branch()
        change = self.client.get(
            reverse('admin:network_branch_change', args=[branch.pk]),
        )
        self.assertNotContains(change, 'Координати введено вручну')
        self.assertContains(change, 'name="map_embed_url"')
        self.assertNotContains(change, 'name="map_url"')
        self.assertNotContains(change, 'name="lat"')
        self.assertNotContains(change, 'name="lng"')
        self.assertContains(change, 'Графік роботи')
        self.assertNotContains(change, 'Графік по днях')
        self.assertNotContains(change, 'Старий текст графіка')
