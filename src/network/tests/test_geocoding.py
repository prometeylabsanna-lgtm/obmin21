import json
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings

from src.core.seo_schema import _department
from src.network import geocoding
from src.network.models import STUB_ADDRESSES, Branch, City, address_is_real


class _Body:
    def __init__(self, payload, raw=None):
        if raw is None:
            raw = json.dumps(payload).encode()
        self.raw = raw

    def read(self, limit=-1):
        if limit is None or limit < 0:
            return self.raw
        return self.raw[:limit]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _house(lat='49.994443', lon='36.232961', **extra):
    item = {
        'lat': lat,
        'lon': lon,
        'addresstype': 'building',
        'type': 'house',
        'address': {'road': 'Сумська', 'house_number': '10'},
    }
    item.update(extra)
    return [item]


class AddressIsRealTests(TestCase):
    def test_stub_list_and_normalization(self):
        self.assertEqual(STUB_ADDRESSES, ('вул. Хрещатик, 1, Київ',))
        self.assertFalse(address_is_real('', 'lviv'))
        self.assertFalse(address_is_real('   ', 'kyiv'))
        self.assertFalse(address_is_real(None, 'kyiv'))
        self.assertFalse(address_is_real('вул. Хрещатик, 1, Київ', 'poltava'))
        self.assertFalse(address_is_real('вул.  Хрещатик, 1,   Київ', 'sumy'))
        self.assertFalse(address_is_real('вул.\u00a0Хрещатик, 1, Київ', None))
        self.assertFalse(address_is_real('вул. Хрещатик, 1, Київ', 'Kyiv'))
        self.assertTrue(address_is_real('вул. Хрещатик, 1, Київ', 'kyiv'))
        self.assertTrue(address_is_real('вул. Сумська, 10, Харків', 'kharkiv'))
        self.assertTrue(address_is_real('вул. Хрещатик - 1, Київ', 'poltava'))

    def test_branch_property_uses_city_slug(self):
        poltava = City.objects.create(name='Полтава', slug='poltava')
        kyiv = City.objects.create(name='Київ', slug='kyiv')
        stub = Branch(city=poltava, address='вул. Хрещатик, 1, Київ')
        capital = Branch(city=kyiv, address='вул. Хрещатик, 1, Київ')
        self.assertFalse(stub.has_real_address)
        self.assertTrue(capital.has_real_address)


@override_settings(SITE_URL='https://maps.example')
class GeocodeBranchTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Харків', slug='kharkiv')
        self.branch = Branch.objects.create(
            city=self.city,
            address='вул. Сумська, 10, Харків',
        )

    def _open(self, payload):
        def _urlopen(request, timeout=None):
            _urlopen.calls.append((request, timeout))
            if isinstance(payload, Exception):
                raise payload
            return _Body(payload)

        _urlopen.calls = []
        return _urlopen

    def test_accepts_house_level_and_sends_nominatim_params(self):
        opener = self._open(_house(lat='49.9944434', lon='36.2329616'))
        with patch('src.network.geocoding.urlopen', opener):
            point = geocoding.geocode_branch(self.branch)
        self.assertEqual(point, (Decimal('49.994443'), Decimal('36.232962')))
        request, timeout = opener.calls[0]
        self.assertEqual(timeout, 5)
        parsed = urlparse(request.full_url)
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, 'nominatim.openstreetmap.org')
        self.assertEqual(parsed.path, '/search')
        query = parse_qs(parsed.query)
        self.assertEqual(query['format'], ['jsonv2'])
        self.assertEqual(query['limit'], ['1'])
        self.assertEqual(query['countrycodes'], ['ua'])
        self.assertEqual(query['q'], ['вул. Сумська, 10, Харків'])
        self.assertEqual(
            request.get_header('User-agent'),
            'Obmin21/1.0 (+maps.example)',
        )

    def test_appends_city_when_missing_from_address(self):
        self.branch.address = 'вул. Тестова, 5'
        opener = self._open(_house())
        with patch('src.network.geocoding.urlopen', opener):
            geocoding.geocode_branch(self.branch)
        query = parse_qs(urlparse(opener.calls[0][0].full_url).query)
        self.assertEqual(query['q'], ['вул. Тестова, 5, Харків'])

    def test_rejects_street_without_house_number(self):
        street = [{
            'lat': '49.99',
            'lon': '36.23',
            'addresstype': 'road',
            'type': 'residential',
            'address': {'road': 'Сумська'},
        }]
        opener = self._open(street)
        with patch('src.network.geocoding.urlopen', opener):
            self.assertIsNone(geocoding.geocode_branch(self.branch))

    def test_accepts_house_number_or_place_type(self):
        numbered = [{
            'lat': '50.45',
            'lon': '30.52',
            'addresstype': 'road',
            'type': 'residential',
            'address': {'house_number': '1'},
        }]
        shop = [{
            'lat': '50.45',
            'lon': '30.52',
            'addresstype': 'shop',
            'type': 'clothes',
            'address': {'road': 'Хрещатик'},
        }]
        for payload in (numbered, shop):
            opener = self._open(payload)
            with patch('src.network.geocoding.urlopen', opener):
                self.assertIsNotNone(geocoding.geocode_branch(self.branch))

    def test_failures_return_none(self):
        cases = (
            TimeoutError('slow'),
            ValueError('bad'),
            [],
            {'error': 'no'},
            'not-json',
        )
        for payload in cases:
            if payload == 'not-json':
                def _urlopen(request, timeout=None, body=_Body(None, raw=b'{')):
                    return body
                with patch('src.network.geocoding.urlopen', _urlopen):
                    self.assertIsNone(geocoding.geocode_branch(self.branch))
                continue
            opener = self._open(payload)
            with patch('src.network.geocoding.urlopen', opener):
                self.assertIsNone(geocoding.geocode_branch(self.branch))

    def test_skips_http_without_real_address(self):
        self.branch.address = 'вул. Хрещатик, 1, Київ'
        self.branch.save(update_fields=['address'])
        with patch('src.network.geocoding.urlopen') as urlopen:
            self.assertIsNone(geocoding.geocode_branch(self.branch))
        urlopen.assert_not_called()

    @override_settings(SITE_URL='')
    def test_user_agent_without_domain(self):
        self.assertEqual(geocoding.nominatim_user_agent(), 'Obmin21/1.0')

    def test_rule_is_documented(self):
        text = geocoding.__doc__
        self.assertIn('coords_manual', text)
        self.assertIn('jsonv2', text)
        self.assertIn('house_number', text)


class GeoJsonLdTests(TestCase):
    def test_geo_follows_real_address(self):
        request = RequestFactory().get('/')
        request._exchange_only = False
        origin = 'https://obmin21.com'
        business = origin + '/#business'
        poltava = City.objects.create(name='Полтава', slug='poltava-geo')
        kyiv = City.objects.create(name='Київ', slug='kyiv')
        stub = Branch.objects.create(
            city=poltava,
            address='вул. Хрещатик, 1, Київ',
            lat=Decimal('49.588267'),
            lng=Decimal('34.551417'),
            is_active=True,
        )
        real = Branch.objects.create(
            city=kyiv,
            address='вул. Хрещатик, 1, Київ',
            lat=Decimal('50.450100'),
            lng=Decimal('30.523400'),
            is_active=True,
        )
        stub_node = _department(stub, request, origin, business)
        real_node = _department(real, request, origin, business)
        self.assertNotIn('geo', stub_node)
        self.assertEqual(real_node['geo']['@type'], 'GeoCoordinates')
        self.assertAlmostEqual(real_node['geo']['latitude'], 50.4501, places=5)
        self.assertAlmostEqual(real_node['geo']['longitude'], 30.5234, places=5)
        self.assertNotIn('49.588267', stub.map_embed_src())
        self.assertIn('50.450100', real.map_embed_src())
