from django.db import models

from src.core.exchange_fields import mode_char, mode_text, resolved_text

SERVICE_BLOCK_DEFAULTS = {
    'obmin-valyut': {
        'text': (
            'Купуйте та продавайте понад 15 валют за актуальним курсом. '
            'Перевіряємо банкноти на місці та видаємо лише справні купюри.'
        ),
        'points': (
            'USD, EUR, PLN, GBP та інші валюти',
            'Фіксація курсу онлайн на 30 хвилин',
            'Без прихованих комісій',
        ),
        'cta': 'Зафіксувати курс',
    },
    'groshovi-perekazy': {
        'text': (
            'Надсилайте гроші по Україні та за кордон готівкою або на картку. '
            'Консультант допоможе обрати найшвидший спосіб.'
        ),
        'points': (
            'Перекази по Україні за кілька хвилин',
            'Міжнародні перекази у 100+ країн',
            'Прозорі тарифи до відправлення',
        ),
        'cta': 'Надіслати переказ',
    },
    'kryptovalyuta': {
        'text': (
            'Обмінюйте USDT, BTC, ETH та інші монети на готівку і навпаки. '
            'Підтвердження транзакції займає кілька хвилин.'
        ),
        'points': (
            'Вигідний курс USDT/UAH',
            'Готівка у відділенні одразу після підтвердження',
            'Допомога з гаманцем для новачків',
        ),
        'cta': 'Обміняти крипту',
    },
    'investytsiine-zoloto': {
        'text': (
            'Злитки різної ваги з сертифікатами для збереження капіталу. '
            'Розповімо про зберігання та зворотний викуп.'
        ),
        'points': (
            'Злитки від 1 до 100 г',
            'Сертифікат на кожен злиток',
            'Зворотний викуп за ринковою ціною',
        ),
        'cta': 'Обрати злиток',
    },
    'optovyi-obmin': {
        'text': (
            'Індивідуальний курс для великих сум і бізнесу. '
            'Підготуємо потрібну суму заздалегідь і проведемо операцію в окремій зоні.'
        ),
        'points': (
            'Індивідуальний курс від 5000 USD',
            'Резервування суми заздалегідь',
            'Конфіденційне обслуговування',
        ),
        'cta': 'Отримати курс',
    },
    'zamina-znoshenykh-kupiur': {
        'text': (
            'Приймаємо надірвані, потерті та старі банкноти. '
            'Проводимо діагностику і пропонуємо обмін на місці.'
        ),
        'points': (
            'Діагностика за кілька хвилин',
            'Долари та євро старого зразка',
            'Вартість відома до операції',
        ),
        'cta': 'Перевірити купюру',
    },
}


class ServiceBlockFields(models.Model):
    block_text = models.TextField('Текст блоку', blank=True)
    block_text_mode = mode_text('Текст блоку для режиму «Лише обмін»')
    block_points = models.TextField(
        'Пункти',
        blank=True,
        help_text='Кожен пункт з нового рядка.',
    )
    block_points_mode = mode_text('Пункти для режиму «Лише обмін»')
    block_cta = models.CharField('Текст кнопки', max_length=80, blank=True)
    block_cta_mode = mode_char('Текст кнопки для режиму «Лише обмін»', 80)

    class Meta:
        abstract = True


def points_as_text(points):
    return '\n'.join(points)


def _points(raw):
    return tuple(line.strip() for line in str(raw or '').splitlines() if line.strip())


def _empty_block():
    return {'text': '', 'points': (), 'cta': ''}


def _mode_block(row):
    from src.core import exchange_mode

    return {
        'text': exchange_mode.mode_text(row, 'block_text'),
        'points': _points(exchange_mode.mode_text(row, 'block_points')),
        'cta': exchange_mode.mode_text(row, 'block_cta'),
    }


def resolve_block(slug):
    from src.content.models import Service
    from src.core.exchange_mode import exchange_only

    default = SERVICE_BLOCK_DEFAULTS.get(slug)
    row = Service.objects.filter(slug=slug).first()
    if exchange_only():
        if default is None:
            if row is None:
                return None
            block = _mode_block(row)
            if not block['text'] and not block['points'] and not block['cta']:
                return None
            return block
        if row is None:
            return _empty_block()
        return _mode_block(row)
    if row is None:
        if default is None:
            return None
        return {
            'text': default['text'],
            'points': default['points'],
            'cta': default['cta'],
        }
    fallback = default or {}
    text = resolved_text(row, 'block_text', fallback.get('text', ''))
    points = _points(row.block_points) or fallback.get('points') or ()
    cta = resolved_text(row, 'block_cta', fallback.get('cta', ''))
    if default is None and not str(text).strip() and not points and not str(cta).strip():
        return None
    return {'text': text, 'points': tuple(points), 'cta': cta}


class ServiceBlockMap:
    def get(self, key, default=None):
        found = resolve_block(key)
        if found is None:
            return default
        return found

    def __contains__(self, key):
        return key in SERVICE_BLOCK_DEFAULTS

    def __getitem__(self, key):
        found = resolve_block(key)
        if found is None:
            raise KeyError(key)
        return found


SERVICE_BLOCKS = ServiceBlockMap()
