import re

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from src.core.exchange_mode import is_exchange_only, mode_text
from src.core.exchange_stopwords import matches_stop_words
from src.core.models import SiteSettings
from src.core.phones import phone_tel
from src.leads.forms import ContactMessageForm, ExchangeRequestForm
from src.leads.services import create_contact_message, create_exchange_request
from src.network.models import Branch
from src.network.selectors import get_city_branches
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_quotes_for_city


def _pair_symbol(pair):
    mark = pair.flag_mark or ''
    if mark and not mark.isascii():
        return mark
    return ''


def _booking_currencies(city):
    items = [{
        'code': 'UAH',
        'name': 'Гривня',
        'buy': '1',
        'sell': '1',
        'pair_id': '',
        'symbol': '₴',
    }]
    rows, _ = get_quotes_for_city(city, RateBoard.RETAIL)
    for row in rows:
        code = (row['pair'].code or '').upper()
        if '/' in code:
            continue
        items.append({
            'code': code,
            'name': row['pair'].name,
            'buy': str(row['quote'].buy),
            'sell': str(row['quote'].sell),
            'pair_id': row['pair'].pk,
            'symbol': _pair_symbol(row['pair']),
        })
    return items


def _telegram_handle(url):
    if not url:
        return '@obmin21'
    match = re.search(r'(?:t\.me/|telegram\.me/)(@?[\w]+)', url)
    if match:
        handle = match.group(1)
        return handle if handle.startswith('@') else f'@{handle}'
    return '@obmin21'


_TME_TAIL = re.compile(r't\.me/([^?#]*)', re.IGNORECASE)


def _plain(value):
    return str(value or '').strip()


def telegram_nick(url):
    """Останній сегмент після t.me/. Порожній URL або без ніка — порожній рядок."""
    raw = _plain(url)
    if not raw:
        return ''
    match = _TME_TAIL.search(raw)
    if not match:
        return ''
    tail = match.group(1).strip().strip('/')
    if not tail:
        return ''
    segment = tail.split('/')[-1].strip().lstrip('@')
    if not segment:
        return ''
    return f'@{segment}'


def _contact_phone(request, site):
    """Телефон відділення, інакше міста, інакше телефон із загальних налаштувань."""
    city = getattr(request, 'city', None)
    branches = getattr(request, 'city_branches', None)
    if branches is None and city is not None:
        branches = get_city_branches(city)
    for branch in branches or []:
        phone = _plain(getattr(branch, 'phone', ''))
        if phone:
            return phone
    if city is not None:
        phone = _plain(getattr(city, 'phone', ''))
        if phone:
            return phone
    return _plain(site.default_phone)


def _visible_copy(value, request):
    text = _plain(value)
    if not text:
        return ''
    if is_exchange_only(request) and matches_stop_words(text):
        return ''
    return text


def _contact_modal_copy(request):
    from src.content.models import ContactsPage, FaqPage

    contacts = ContactsPage.load()
    faq = FaqPage.load()
    heading = _visible_copy(
        mode_text(contacts, 'heading', request=request),
        request,
    )
    accent = _visible_copy(contacts.title_accent, request) if heading else ''
    return {
        'modal_title': heading,
        'modal_accent': accent,
        'phone_label': _visible_copy(faq.cta_phone, request),
        'telegram_label': _visible_copy(faq.cta_telegram, request),
    }


def _modal_context(request, form=None):
    city = request.city
    currencies = _booking_currencies(city)
    codes = {item['code'] for item in currencies}
    source = request.POST if request.method == 'POST' else request.GET
    pair_id = source.get('pair')
    initial_from = (source.get('from') or 'USD').upper()
    initial_to = (source.get('to') or 'UAH').upper()
    if pair_id and 'from' not in source and 'to' not in source:
        pair = CurrencyPair.objects.visible().filter(pk=pair_id, is_active=True).first()
        if pair and pair.code and '/' not in pair.code:
            initial_from = pair.code.upper()
            initial_to = 'UAH'
    if initial_from not in codes:
        initial_from = 'USD' if 'USD' in codes else next(iter(codes), 'UAH')
    if initial_to not in codes or initial_to == initial_from:
        initial_to = 'UAH' if 'UAH' in codes and initial_from != 'UAH' else (
            next((c for c in codes if c != initial_from), 'UAH')
        )
    amount = source.get('amount_give') or '1000'
    board = source.get('board') or RateBoard.RETAIL
    if board not in RateBoard.values:
        board = RateBoard.RETAIL
    direction = source.get('direction') or 'sell'
    branch = get_city_branches(city).first() if city else None
    resolved_pair = None
    if pair_id:
        resolved_pair = CurrencyPair.objects.visible().filter(
            pk=pair_id,
            is_active=True,
        ).first()
    if resolved_pair is None:
        for item in currencies:
            if item['code'] == initial_from and item.get('pair_id'):
                resolved_pair = CurrencyPair.objects.visible().filter(
                    pk=item['pair_id'],
                    is_active=True,
                ).first()
                break
    places = []
    for item in getattr(request, 'cities', []):
        branch_rows = [
            {'id': b.pk, 'address': b.address}
            for b in get_city_branches(item)
        ]
        if branch_rows:
            places.append({
                'id': item.pk,
                'name': item.name,
                'slug': item.slug,
                'branches': branch_rows,
            })
    selected_city = city
    raw_branch = form['branch'].value() if form is not None else None
    if raw_branch:
        chosen = Branch.objects.filter(pk=raw_branch, is_active=True).select_related('city').first()
        if chosen and chosen.city_id:
            selected_city = chosen.city
    site = SiteSettings.load()
    phone = ''
    if city and city.phone:
        phone = city.phone
    elif site.default_phone:
        phone = site.default_phone
    telegram_url = site.telegram_url or 'https://t.me/obmin21'
    if form is None:
        form = ExchangeRequestForm(city=city, initial={
            'pair': resolved_pair.pk if resolved_pair else None,
            'board': board,
            'direction': direction,
            'amount_give': amount,
            'branch': branch.pk if branch else None,
        })
    return {
        'form': form,
        'currencies': currencies,
        'initial_from': initial_from,
        'initial_to': initial_to,
        'initial_amount': amount,
        'branch_address': branch.address if branch else '',
        'branches': list(get_city_branches(selected_city)) if selected_city else [],
        'booking_places': places,
        'booking_city_id': selected_city.pk if selected_city else '',
        'booking_direct': request.method != 'POST' and request.GET.get('direct') == '1',
        'phone_display': phone,
        'phone_tel': phone_tel(phone),
        'telegram_url': telegram_url,
        'telegram_handle': _telegram_handle(telegram_url),
    }


def _render_contact_modal(request):
    site = SiteSettings.load()
    phone = _contact_phone(request, site)
    telegram_url = _plain(site.telegram_url)
    context = _contact_modal_copy(request)
    context.update({
        'phone_display': phone,
        'phone_tel': phone_tel(phone),
        'telegram_url': telegram_url,
        'telegram_nick': telegram_nick(telegram_url),
    })
    return render(request, 'partials/modal_contact.html', context)


@require_http_methods(['GET', 'POST'])
def exchange_request_modal(request):
    if request.method != 'POST':
        return _render_contact_modal(request)
    city = request.city
    form = ExchangeRequestForm(request.POST, city=city)
    if form.is_valid() and city is not None:
        branch = form.cleaned_data.get('branch')
        lead_city = branch.city if branch is not None else city
        obj = create_exchange_request(cleaned=form.cleaned_data, city=lead_city)
        return render(request, 'partials/form_success.html', {
            'title': 'Заявку прийнято',
            'message': (
                f'Курс зафіксовано до {obj.expires_at:%H:%M %d.%m.%Y}. '
                f'Чекаємо вас у відділенні: {obj.branch.address}.'
            ),
        })
    if city is None:
        return render(request, 'partials/form_error.html', {
            'title': 'Перевірте дані',
            'message': 'Оберіть місто і спробуйте ще раз або зателефонуйте.',
        }, status=422)
    return render(
        request,
        'partials/modal_request.html',
        _modal_context(request, form=form),
        status=422,
    )


@require_http_methods(['GET'])
def calc_modal(request):
    return _render_contact_modal(request)


@require_http_methods(['GET'])
def contact_modal(request):
    return _render_contact_modal(request)


@require_http_methods(['POST'])
def contact_submit(request):
    form = ContactMessageForm(request.POST)
    if form.is_valid():
        create_contact_message(cleaned=form.cleaned_data, city=request.city)
        return render(request, 'partials/form_success_inline.html', {
            'title': 'Повідомлення надіслано',
            'message': 'Ми звʼяжемося з вами найближчим часом.',
        })
    response = _render_contact_modal(request)
    response.status_code = 422
    return response
