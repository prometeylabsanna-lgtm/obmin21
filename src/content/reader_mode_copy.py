"""Порожні тексти режиму «Лише обмін» для карток, міст і відгуків.

Повтор не перезаписує правки. Картку з стоп-словом у базовому тексті не заповнює.
"""

from src.core.exchange_stopwords import matches_stop_words
from src.core.plain_text import plain_text

CITIES_PAGE_MODE_COPY = {
    'title_mode': 'Міста обміну',
    'intro_mode': (
        'Відділення обміну готівкової валюти в містах мережі Обмін21. '
        'Оберіть місто, щоб побачити адресу та актуальний курс.'
    ),
}

REVIEWS_PAGE_MODE_COPY = {
    'title_mode': 'Відгуки про обмін',
    'seo_title_mode': 'Відгуки про обмін готівкової валюти',
    'seo_description_mode': (
        'Відгуки клієнтів про обмін долара та євро у відділеннях Обмін21.'
    ),
}

PAGE_MODE_COPY = {
    'content.CitiesPage': CITIES_PAGE_MODE_COPY,
    'content.ReviewsPage': REVIEWS_PAGE_MODE_COPY,
}


def exchange_plain(value):
    return ' '.join(plain_text(str(value or '')).split())


def _blank(value):
    return not str(value or '').strip()


def stat_base_is_clean(number, text):
    number_plain = exchange_plain(number)
    text_plain = exchange_plain(text)
    return not matches_stop_words(number, text, number_plain, text_plain)


def _fill_blank(model, row, mapping):
    names = {field.name for field in model._meta.fields}
    updates = {}
    for name, text in mapping.items():
        if name not in names or not _blank(getattr(row, name, '')):
            continue
        if matches_stop_words(text):
            continue
        limit = getattr(model._meta.get_field(name), 'max_length', None)
        if limit and len(text) > limit:
            continue
        updates[name] = text
    if updates:
        model.objects.filter(pk=row.pk).update(**updates)


def fill_home_stat_mode(apps):
    HomeStat = apps.get_model('content', 'HomeStat')
    names = {field.name for field in HomeStat._meta.fields}
    if 'number_mode' not in names or 'text_mode' not in names:
        return
    number_limit = HomeStat._meta.get_field('number_mode').max_length
    for row in HomeStat.objects.all().order_by('pk'):
        number_plain = exchange_plain(getattr(row, 'number', ''))
        text_plain = exchange_plain(getattr(row, 'text', ''))
        if not stat_base_is_clean(getattr(row, 'number', ''), getattr(row, 'text', '')):
            continue
        updates = {}
        if (
            _blank(getattr(row, 'number_mode', ''))
            and number_plain
            and (not number_limit or len(number_plain) <= number_limit)
            and not matches_stop_words(number_plain)
        ):
            updates['number_mode'] = number_plain
        if (
            _blank(getattr(row, 'text_mode', ''))
            and text_plain
            and not matches_stop_words(text_plain)
        ):
            updates['text_mode'] = text_plain
        if updates:
            HomeStat.objects.filter(pk=row.pk).update(**updates)


def fill_reader_mode_fields(apps, schema_editor):
    """Заповнює порожні поля режиму. Повтор не перезаписує правки."""
    fill_home_stat_mode(apps)
    for label, mapping in PAGE_MODE_COPY.items():
        app_label, model_name = label.split('.')
        model = apps.get_model(app_label, model_name)
        field_names = {field.name for field in model._meta.fields}
        if any(name not in field_names for name in mapping):
            continue
        row = model.objects.filter(pk=1).first()
        if row is None:
            row = model.objects.create(pk=1)
        _fill_blank(model, row, mapping)
