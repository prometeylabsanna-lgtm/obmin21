"""Порожні title/meta тексти режиму «Лише обмін». Повтор не перезаписує правки."""

from src.content.stage3_fill import SERVICES_PAGE_MODE_COPY
from src.core.exchange_stopwords import matches_stop_words

EXCHANGE_SHORT_DESC_MODE = (
    'Купівля та продаж готівкової валюти за актуальним курсом у відділеннях Обмін21.'
)

_EXCHANGE_SLUGS = frozenset({'obmin-valyut'})
_SKIP_SERVICE_MARKERS = (
    'крипт',
    'krypto',
    'crypto',
    'bitcoin',
    'бітко',
    'битко',
    'swift',
    'переказ',
    'perekaz',
    'transfer',
    'золот',
    'zolot',
    'gold',
    'оптов',
    'optov',
    'wholesale',
    'зношен',
    'znosh',
    'worn',
    'usdt',
    'usdc',
    'tether',
    'стейблко',
)

PAGE_MODE_COPY = {
    'content.ServicesPage': {
        'title_mode': 'Обмін валют',
        'seo_title_mode': 'Обмін готівкової валюти — Обмін21',
        'intro_mode': (
            'Обмін долара, євро та інших готівкових валют у відділеннях Обмін21. '
            'Курс можна зафіксувати онлайн перед візитом.'
        ),
        **SERVICES_PAGE_MODE_COPY,
    },
    'content.AdvantagesPage': {
        'title_mode': 'Переваги обміну',
        'hero_lead_mode': (
            'Вигідний курс без комісій, фіксація онлайн і перевірка кожної купюри. '
            'Обмін готівки відбувається у відділенні.'
        ),
        'seo_title_mode': 'Переваги обміну готівкової валюти',
        'seo_description_mode': (
            'Чому обирають Обмін21: вигідний курс готівкової валюти, '
            'фіксація онлайн і перевірка купюр у відділенні.'
        ),
    },
    'content.ContactsPage': {
        'title_mode': 'Контакти',
        'heading_mode': 'Зв’яжіться',
        'seo_title_mode': 'Контакти відділень обміну валют',
        'seo_description_mode': (
            'Телефон, графік і адреси відділень Обмін21 для обміну готівкової валюти.'
        ),
    },
    'content.FaqPage': {
        'title_mode': 'Питання про обмін',
        'lead_mode': (
            'Короткі відповіді про курс, документи та візит до відділення '
            'для обміну готівки.'
        ),
        'seo_title_mode': 'Питання та відповіді про обмін валют',
        'seo_description_mode': (
            'Як зафіксувати курс, які документи потрібні та як проходить '
            'обмін готівки в Обмін21.'
        ),
    },
    'content.BlogPage': {
        'title_mode': 'Статті про обмін',
        'intro_mode': (
            'Пояснюємо, як працює курс готівкової валюти і як підготуватися '
            'до обміну у відділенні.'
        ),
        'seo_title_mode': 'Статті про обмін готівкової валюти',
        'seo_description_mode': (
            'Матеріали про курс долара та євро, фіксацію курсу '
            'і підготовку до обміну готівки.'
        ),
    },
    'content.RatesPage': {
        'title_mode': 'Курси валют',
        'intro_mode': (
            'Актуальні курси купівлі та продажу готівкової валюти '
            'у відділеннях Обмін21. Зафіксуйте курс онлайн і приходьте без черги.'
        ),
        'seo_title_mode': 'Курси готівкової валюти',
        'seo_description_mode': (
            'Актуальні курси купівлі та продажу долара, євро та інших '
            'готівкових валют у відділеннях Обмін21.'
        ),
    },
}


def _blank(value):
    return not str(value or '').strip()


def service_blob(row):
    return '\n'.join((
        str(getattr(row, 'slug', '') or ''),
        str(getattr(row, 'title', '') or ''),
    )).casefold()


def is_exchange_service(row):
    """Готівковий обмін валют. Крипто, золото, перекази, SWIFT, опт і зношені — ні."""
    blob = service_blob(row)
    if any(marker in blob for marker in _SKIP_SERVICE_MARKERS):
        return False
    slug = str(getattr(row, 'slug', '') or '').casefold()
    if slug in _EXCHANGE_SLUGS or slug.startswith('obmin-'):
        return True
    title = str(getattr(row, 'title', '') or '').casefold()
    return 'обмін' in title and 'валют' in title


def _fill_blank(model, row, mapping):
    names = {field.name for field in model._meta.fields}
    updates = {}
    for name, text in mapping.items():
        if name not in names or not _blank(getattr(row, name, '')):
            continue
        if matches_stop_words(text):
            continue
        updates[name] = text
    if updates:
        model.objects.filter(pk=row.pk).update(**updates)


def _fill_exchange_services(apps):
    Service = apps.get_model('content', 'Service')
    if not any(field.name == 'short_desc_mode' for field in Service._meta.fields):
        return
    for row in Service.objects.all().order_by('pk'):
        if not is_exchange_service(row):
            continue
        _fill_blank(Service, row, {'short_desc_mode': EXCHANGE_SHORT_DESC_MODE})


def fill_page_meta_mode(apps, schema_editor):
    """Заповнює порожні тексти сторінок і карток обміну. Повтор не перезаписує правки."""
    for label, mapping in PAGE_MODE_COPY.items():
        app_label, model_name = label.split('.')
        model = apps.get_model(app_label, model_name)
        row = model.objects.filter(pk=1).first()
        if row is None:
            continue
        _fill_blank(model, row, mapping)
    _fill_exchange_services(apps)
