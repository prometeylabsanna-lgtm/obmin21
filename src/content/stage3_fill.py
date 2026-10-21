import copy


def _blank(value):
    return not str(value or '').strip()


def _json_empty(value):
    if value in (None, '', [], ()):
        return True
    return isinstance(value, dict) and not value


def fill_content_copy(apps, schema_editor):
    from src.content.advantages_fields import CMP_THEM_HTML, CMP_US_HTML, STAT_TEXTS
    from src.content.home_copy import HOME_COPY_DEFAULTS
    from src.content.service_blocks import SERVICE_BLOCK_DEFAULTS, points_as_text

    Service = apps.get_model('content', 'Service')
    for slug, block in SERVICE_BLOCK_DEFAULTS.items():
        row = Service.objects.filter(slug=slug).first()
        if row is None:
            continue
        updates = {}
        if _blank(row.block_text):
            updates['block_text'] = block['text']
        if _blank(row.block_points):
            updates['block_points'] = points_as_text(block['points'])
        if _blank(row.block_cta):
            updates['block_cta'] = block['cta']
        if updates:
            Service.objects.filter(pk=row.pk).update(**updates)

    AdvantagesPage = apps.get_model('content', 'AdvantagesPage')
    page = AdvantagesPage.objects.filter(pk=1).first()
    if page is not None:
        updates = {}
        if _blank(page.cmp_us_html):
            updates['cmp_us_html'] = CMP_US_HTML
        if _blank(page.cmp_them_html):
            updates['cmp_them_html'] = CMP_THEM_HTML
        for index, text in STAT_TEXTS.items():
            field_name = f'stat_{index}_text'
            if _blank(getattr(page, field_name)):
                updates[field_name] = text
        if updates:
            AdvantagesPage.objects.filter(pk=page.pk).update(**updates)

    HomePage = apps.get_model('content', 'HomePage')
    home = HomePage.objects.filter(pk=1).first()
    if home is not None:
        updates = {}
        for name, default in HOME_COPY_DEFAULTS.items():
            if _blank(getattr(home, name)):
                updates[name] = default
        if updates:
            HomePage.objects.filter(pk=home.pk).update(**updates)


def fill_article_layouts(apps, schema_editor):
    from src.blog.article_data import BY_SLUG

    Post = apps.get_model('blog', 'Post')
    for slug, payload in BY_SLUG.items():
        row = Post.objects.filter(slug=slug).first()
        if row is None or not _json_empty(row.layout):
            continue
        Post.objects.filter(pk=row.pk).update(layout=copy.deepcopy(payload))


SERVICES_PAGE_MODE_COPY = {
    'hero_text_mode': (
        'Обмін готівкової валюти за актуальним курсом із фіксацією онлайн.'
    ),
    'seo_description_mode': (
        'Обмін долара, євро та інших готівкових валют у відділеннях Обмін21. '
        'Курс можна зафіксувати онлайн.'
    ),
}


def fill_services_page_mode(apps, schema_editor):
    """Заповнює порожні тексти режиму сторінки послуг. Повтор не перезаписує правки."""
    ServicesPage = apps.get_model('content', 'ServicesPage')
    page = ServicesPage.objects.filter(pk=1).first()
    if page is None:
        return
    updates = {}
    for name, text in SERVICES_PAGE_MODE_COPY.items():
        if _blank(getattr(page, name, '')):
            updates[name] = text
    if updates:
        ServicesPage.objects.filter(pk=page.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    return None
