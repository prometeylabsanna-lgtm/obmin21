from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from src.core.templatetags.content_format import format_rate
from src.leads.forms import ContactMessageForm, ExchangeRequestForm
from src.leads.services import create_contact_message, create_exchange_request
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_active_pairs, get_quote


@require_http_methods(['GET', 'POST'])
def exchange_request_modal(request):
    city = request.city
    initial = {
        'pair': request.GET.get('pair') or request.POST.get('pair'),
        'board': request.GET.get('board', RateBoard.RETAIL),
        'direction': request.GET.get('direction', 'sell'),
        'amount_give': request.GET.get('amount_give', ''),
        'amount_receive': request.GET.get('amount_receive', ''),
        'rate_fixed': request.GET.get('rate_fixed', ''),
    }
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
    else:
        form = ExchangeRequestForm(city=city)
        for key, value in initial.items():
            if value and key in form.fields:
                if key in ('amount_give', 'amount_receive'):
                    form.fields[key].initial = format_rate(value, 'compact')
                elif key == 'rate_fixed':
                    form.fields[key].initial = format_rate(value, 'auto')
                else:
                    form.fields[key].initial = value
        pair_id = initial.get('pair')
        if pair_id and not initial.get('rate_fixed'):
            pair = CurrencyPair.objects.filter(pk=pair_id).first()
            if pair:
                quote = get_quote(pair, city, initial.get('board') or RateBoard.RETAIL)
                if quote:
                    direction = initial.get('direction') or 'sell'
                    rate = quote.buy if direction == 'sell' else quote.sell
                    form.fields['rate_fixed'].initial = format_rate(rate, 'auto')

    return render(request, 'partials/modal_request.html', {
        'form': form,
        'pairs': get_active_pairs(),
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
