import re

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from src.core.models import SiteSettings
from src.leads.forms import ContactMessageForm, ExchangeRequestForm
from src.leads.services import create_contact_message, create_exchange_request
from src.network.selectors import get_city_branches
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_active_pairs, get_quote, get_quotes_for_city


def _booking_currencies(city):
    items = [{'code': 'UAH', 'name': 'Гривня', 'buy': '1', 'sell': '1', 'pair_id': ''}]
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


def _phone_tel(phone):
    digits = re.sub(r'\D+', '', phone or '')
    if not digits:
        return '+380444444444'
    if digits.startswith('380'):
        return f'+{digits}'
    if digits.startswith('0') and len(digits) == 10:
        return f'+38{digits}'
    return f'+{digits}'


@require_http_methods(['GET', 'POST'])
def exchange_request_modal(request):
    city = request.city
    if request.method == 'POST':
        form = ExchangeRequestForm(request.POST, city=city)
        if form.is_valid() and city is not None:
            obj = create_exchange_request(cleaned=form.cleaned_data, city=city)
            return render(request, 'partials/form_success.html', {
                'title': 'Заявку прийнято',
                'message': (
                    f'Курс зафіксовано до {obj.expires_at:%H:%M %d.%m.%Y}. '
                    f'Чекаємо вас у відділенні: {obj.branch.address}.'
                ),
            })
        return render(request, 'partials/form_success.html', {
            'title': 'Перевірте дані',
            'message': 'Не вдалося зберегти заявку. Спробуйте ще раз або зателефонуйте.',
        })

    currencies = _booking_currencies(city)
    codes = {item['code'] for item in currencies}
    pair_id = request.GET.get('pair')
    initial_from = (request.GET.get('from') or 'USD').upper()
    initial_to = (request.GET.get('to') or 'UAH').upper()
    if pair_id:
        pair = CurrencyPair.objects.filter(pk=pair_id).first()
        if pair and pair.code and '/' not in pair.code:
            initial_from = pair.code.upper()
            initial_to = 'UAH'
    if initial_from not in codes:
        initial_from = 'USD' if 'USD' in codes else next(iter(codes), 'UAH')
    if initial_to not in codes or initial_to == initial_from:
        initial_to = 'UAH' if 'UAH' in codes and initial_from != 'UAH' else (
            next((c for c in codes if c != initial_from), 'UAH')
        )
    amount = request.GET.get('amount_give') or '1000'
    branch = get_city_branches(city).first() if city else None
    site = SiteSettings.load()
    phone = ''
    if city and city.phone:
        phone = city.phone
    elif site.default_phone:
        phone = site.default_phone
    telegram_url = site.telegram_url or 'https://t.me/obmin21'

    return render(request, 'partials/modal_request.html', {
        'currencies': currencies,
        'initial_from': initial_from,
        'initial_to': initial_to,
        'initial_amount': amount,
        'branch_address': branch.address if branch else '',
        'phone_display': phone or '+38 (044) 444 44 44',
        'phone_tel': _phone_tel(phone),
        'telegram_url': telegram_url,
        'telegram_handle': _telegram_handle(telegram_url),
    })


@require_http_methods(['GET'])
def calc_modal(request):
    city = request.city
    rows = []
    for pair in get_active_pairs():
        quote = get_quote(pair, city, RateBoard.RETAIL)
        if quote:
            rows.append({'pair': pair, 'quote': quote})
    return render(request, 'partials/modal_calc.html', {
        'calc_rows': rows,
    })


@require_http_methods(['POST'])
def contact_submit(request):
    form = ContactMessageForm(request.POST)
    if form.is_valid():
        create_contact_message(cleaned=form.cleaned_data, city=request.city)
        return render(request, 'partials/form_success_inline.html', {
            'title': 'Повідомлення надіслано',
            'message': 'Ми звʼяжемося з вами найближчим часом.',
        })
    return render(request, 'partials/contact_form.html', {
        'form': form,
    }, status=422)
