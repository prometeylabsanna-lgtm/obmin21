def _blank(value):
    return not str(value or '').strip()


CITY_MODE_COPY = {
    'banner_title_mode': 'Обмін валют',
    'banner_suffix_mode': 'за вигідним курсом',
    'banner_text_mode': 'Фіксуйте курс онлайн та обмінюйте за вигідним курсом',
    'banner_button_mode': 'Зафіксувати курс',
    'seo_title_mode': 'Обмін валют у відділеннях Обмін21',
    'seo_description_mode': (
        'Готівковий обмін долара та євро за актуальним курсом. '
        'Зафіксуйте курс онлайн перед візитом до відділення.'
    ),
}


def fill_city_banner_seo_mode(apps, schema_editor):
    """Заповнює порожні тексти режиму міста. Повтор не перезаписує правки."""
    City = apps.get_model('network', 'City')
    names = {field.name for field in City._meta.fields}
    for row in City.objects.all().order_by('pk'):
        updates = {}
        for name, text in CITY_MODE_COPY.items():
            if name not in names or not _blank(getattr(row, name, '')):
                continue
            updates[name] = text
        if updates:
            City.objects.filter(pk=row.pk).update(**updates)


def fill_city_name_mode(apps, schema_editor):
    """Порожнє name_mode стає назвою міста. Повтор не перезаписує правки."""
    City = apps.get_model('network', 'City')
    if not any(field.name == 'name_mode' for field in City._meta.fields):
        return
    limit = City._meta.get_field('name_mode').max_length
    for row in City.objects.all().order_by('pk'):
        if not _blank(getattr(row, 'name_mode', '')):
            continue
        name = str(getattr(row, 'name', '') or '').strip()
        if not name or (limit and len(name) > limit):
            continue
        City.objects.filter(pk=row.pk).update(name_mode=name)
