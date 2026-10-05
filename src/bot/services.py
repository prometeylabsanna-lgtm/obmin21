from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.db import transaction

from src.bot.models import BotSession, TelegramProfile
from src.bot.states import BotState
from src.leads.models import ExchangeRequest
from src.leads.services import (
    create_contact_message,
    create_exchange_request,
    normalize_phone,
    validate_phone,
)
from src.network.models import Branch, City
from src.network.selectors import get_active_cities, get_city_branches, get_default_city
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city

logger = logging.getLogger(__name__)

MAX_AMOUNT = Decimal('9999999999.99')
AMOUNT_Q = Decimal('0.01')


def upsert_profile(from_user) -> TelegramProfile:
    chat_id = str(from_user.id)
    defaults = {
        'username': (from_user.username or '')[:64],
        'first_name': (from_user.first_name or '')[:128],
        'last_name': (from_user.last_name or '')[:128],
    }
    profile, _ = TelegramProfile.objects.update_or_create(
        chat_id=chat_id,
        defaults=defaults,
    )
    return profile


def get_session(chat_id: str) -> BotSession:
    session, _ = BotSession.objects.get_or_create(
        chat_id=str(chat_id),
        defaults={'state': BotState.IDLE, 'data': {}},
    )
    return session


@transaction.atomic
def patch_session(chat_id: str, *, state: str | None = None, **fields) -> BotSession:
    session = get_session(chat_id)
    data = dict(session.data or {})
    for key, value in fields.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    session.data = data
    if state is not None:
        session.state = state
    session.save(update_fields=['state', 'data', 'updated_at'])
    return session


def clear_session(chat_id: str) -> None:
    BotSession.objects.filter(chat_id=str(chat_id)).update(
        state=BotState.IDLE,
        data={},
    )


def set_profile_city(chat_id: str, city: City) -> None:
    TelegramProfile.objects.filter(chat_id=str(chat_id)).update(city=city)


def remember_contacts(chat_id: str, *, name: str | None = None, phone: str | None = None) -> None:
    updates: dict[str, Any] = {}
    if name:
        updates['display_name'] = name[:120]
    if phone:
        updates['phone'] = normalize_phone(phone)[:32]
    if updates:
        TelegramProfile.objects.filter(chat_id=str(chat_id)).update(**updates)


def list_cities():
    return list(get_active_cities())


def city_by_id(city_id: int) -> City | None:
    return City.objects.filter(pk=city_id, is_active=True).first()


def resolve_city(profile: TelegramProfile | None, data: dict) -> City | None:
    city_id = data.get('city_id')
    if city_id:
        city = city_by_id(int(city_id))
        if city:
            return city
    if profile and profile.city_id:
        return profile.city if profile.city.is_active else None
    return get_default_city()


def exchange_pairs():
    return list(
        CurrencyPair.objects.filter(is_active=True).exclude(code__contains='/')
    )


def pair_by_id(pair_id: int) -> CurrencyPair | None:
    return CurrencyPair.objects.filter(pk=pair_id, is_active=True).first()


def branch_by_id(branch_id: int, city: City) -> Branch | None:
    return get_city_branches(city).filter(pk=branch_id).first()


def parse_amount(raw: str) -> Decimal | None:
    text = (raw or '').strip().replace(' ', '').replace(',', '.')
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        return None
    if value <= 0 or value > MAX_AMOUNT:
        return None
    return value.quantize(AMOUNT_Q, rounding=ROUND_HALF_UP)


def quote_amounts(pair: CurrencyPair, city: City, direction: str, amount_give: Decimal):
    quote = get_quote(pair, city, RateBoard.RETAIL)
    if quote is None:
        return None
    if direction == ExchangeRequest.Direction.SELL:
        rate = quote.buy
        amount_receive = (amount_give * rate).quantize(AMOUNT_Q, rounding=ROUND_HALF_UP)
    else:
        rate = quote.sell
        if rate <= 0:
            return None
        amount_receive = (amount_give / rate).quantize(AMOUNT_Q, rounding=ROUND_HALF_UP)
    return {
        'quote': quote,
        'rate': rate,
        'amount_give': amount_give,
        'amount_receive': amount_receive,
    }


def format_rates(city: City) -> str:
    rows, updated = get_quotes_for_city(city, RateBoard.RETAIL)
    if not rows:
        return ''
    lines = [f'Курси роздріб, {city.name} (куп / прод):']
    for row in rows:
        pair = row['pair']
        quote = row['quote']
        lines.append(f'{pair.code}: {quote.buy} / {quote.sell}')
    if updated:
        lines.append(f'Оновлено: {updated:%d.%m.%Y %H:%M}')
    return '\n'.join(lines)


def format_branches(city: City) -> str:
    branches = list(get_city_branches(city))
    if not branches:
        return ''
    lines = [f'Відділення, {city.name}:']
    for branch in branches:
        phone = branch.phone or city.phone
        extra = f'\n{phone}' if phone else ''
        hours = f'\n{branch.hours}' if branch.hours else ''
        lines.append(f'• {branch.address}{hours}{extra}')
    return '\n'.join(lines)


def is_valid_name(name: str) -> bool:
    clean = (name or '').strip()
    return 2 <= len(clean) <= 120


def is_valid_feedback(text: str) -> bool:
    clean = (text or '').strip()
    return 2 <= len(clean) <= 2000


def submit_exchange(chat_id: str, profile: TelegramProfile, data: dict):
    city = resolve_city(profile, data)
    pair = pair_by_id(int(data['pair_id']))
    branch = branch_by_id(int(data['branch_id']), city) if city else None
    direction = data['direction']
    amount = parse_amount(str(data['amount_give']))
    name = (data.get('name') or profile.display_name or profile.first_name or '').strip()
    phone = normalize_phone(data.get('phone') or profile.phone or '')
    if not city or not pair or not branch or amount is None:
        raise ValueError('incomplete exchange payload')
    if not validate_phone(phone) or not is_valid_name(name):
        raise ValueError('invalid contacts')
    calc = quote_amounts(pair, city, direction, amount)
    if calc is None:
        raise ValueError('no quote')
    username = profile.username
    messenger = f'@{username}' if username else 'Telegram'
    cleaned = {
        'name': name,
        'phone': phone,
        'messenger': messenger[:80],
        'pair': pair,
        'board': RateBoard.RETAIL,
        'direction': direction,
        'amount_give': calc['amount_give'],
        'amount_receive': calc['amount_receive'],
        'rate_fixed': calc['rate'],
        'branch': branch,
    }
    return create_exchange_request(
        cleaned=cleaned,
        city=city,
        source='telegram',
        telegram_chat_id=str(chat_id),
    )


def submit_feedback(chat_id: str, profile: TelegramProfile, data: dict):
    city = resolve_city(profile, data)
    name = (data.get('name') or profile.display_name or profile.first_name or '').strip()
    phone = normalize_phone(data.get('phone') or profile.phone or '')
    message = (data.get('message') or '').strip()
    if not validate_phone(phone) or not is_valid_name(name) or not is_valid_feedback(message):
        raise ValueError('invalid feedback')
    return create_contact_message(
        cleaned={'name': name, 'phone': phone, 'message': message},
        city=city,
        source='telegram',
        telegram_chat_id=str(chat_id),
    )
