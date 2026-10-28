"""FAQPage і відділення в JSON-LD. Порожнє поле не вигадуємо."""

from html import unescape

from django.utils.html import strip_tags

from src.core.exchange_mode import is_exchange_only, mode_text
from src.network.hours import open_slots, opening_hours_specification


def _plain(value):
    return ' '.join(unescape(strip_tags(str(value or ''))).split())


def _kept(value, request):
    from src.core.seo import _dirty, _one_line

    text = _one_line(_plain(value))
    if not text:
        return ''
    if is_exchange_only(request) and _dirty(text):
        return ''
    return text


def _visible_faq(request):
    match = getattr(request, 'resolver_match', None)
    if match is None:
        return []
    if match.namespace == 'core' and match.url_name == 'home':
        limit = 8
    elif match.namespace == 'content' and match.url_name == 'faq':
        limit = None
    else:
        return []
    from src.content.faq_defaults import public_faq_items

    items = list(public_faq_items(limit=limit))
    if is_exchange_only(request):
        items = [item for item in items if getattr(item, 'exchange_safe', False)]
    return items


def faq_node(request, canonical):
    """Ті самі питання, що малює блок FAQ на головній і на /faq/."""
    questions = []
    for item in _visible_faq(request):
        question = _kept(getattr(item, 'question', ''), request)
        answer = _kept(getattr(item, 'answer', ''), request)
        raw_question = _plain(getattr(item, 'question', ''))
        raw_answer = _plain(getattr(item, 'answer', ''))
        if is_exchange_only(request) and (question != raw_question or answer != raw_answer):
            continue
        if not question or not answer:
            continue
        questions.append({
            '@type': 'Question',
            'name': question,
            'acceptedAnswer': {
                '@type': 'Answer',
                'text': answer,
            },
        })
    if not questions:
        return None
    return {
        '@type': 'FAQPage',
        '@id': canonical + '#faq',
        'mainEntity': questions,
    }


def _coord(value):
    if value is None:
        return None
    return float(value)


def _department(branch, request, origin, business_id):
    city = getattr(branch, 'city', None)
    locality = ''
    if city is not None:
        locality = _kept(mode_text(city, 'name', request), request)
    street = _kept(getattr(branch, 'address', ''), request)
    hours = _kept(getattr(branch, 'hours', ''), request)
    phone = _kept(getattr(branch, 'phone', ''), request)
    address = {}
    if street:
        address['streetAddress'] = street
    if locality:
        address['addressLocality'] = locality
    latitude = _coord(getattr(branch, 'lat', None))
    longitude = _coord(getattr(branch, 'lng', None))
    node = {
        '@type': ['FinancialService', 'LocalBusiness'],
        '@id': f'{origin}/#branch-{branch.pk}',
    }
    name_parts = [part for part in (locality, street) if part]
    if name_parts:
        node['name'] = ', '.join(name_parts)
    if address:
        address['@type'] = 'PostalAddress'
        node['address'] = address
    if latitude is not None and longitude is not None:
        node['geo'] = {
            '@type': 'GeoCoordinates',
            'latitude': latitude,
            'longitude': longitude,
        }
    if hours:
        node['openingHours'] = hours
    spec = opening_hours_specification(open_slots(branch) or [])
    if spec:
        node['openingHoursSpecification'] = spec
    if phone:
        node['telephone'] = phone
    kept = (
        'name',
        'address',
        'geo',
        'openingHours',
        'openingHoursSpecification',
        'telephone',
    )
    if not any(key in node for key in kept):
        return None
    node['parentOrganization'] = {'@id': business_id}
    return node


def branch_departments(request):
    from src.network.models import Branch
    from src.core.seo import site_origin

    origin = site_origin()
    business_id = origin + '/#business'
    rows = (
        Branch.objects.filter(is_active=True, city__is_active=True)
        .select_related('city')
        .prefetch_related('opening_hours')
        .order_by('city__sort_order', 'city_id', 'sort_order', 'id')
    )
    nodes = []
    for branch in rows:
        node = _department(branch, request, origin, business_id)
        if node is not None:
            nodes.append(node)
    return nodes
