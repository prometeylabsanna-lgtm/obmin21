import copy

from src.core.deploy_seed import empty_needs_seed, json_needs_seed


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
        if empty_needs_seed(row.block_text, schema_editor):
            updates['block_text'] = block['text']
        if empty_needs_seed(row.block_points, schema_editor):
            updates['block_points'] = points_as_text(block['points'])
        if empty_needs_seed(row.block_cta, schema_editor):
            updates['block_cta'] = block['cta']
        if updates:
            Service.objects.filter(pk=row.pk).update(**updates)

    AdvantagesPage = apps.get_model('content', 'AdvantagesPage')
    page = AdvantagesPage.objects.filter(pk=1).first()
    if page is not None:
        updates = {}
        if empty_needs_seed(page.cmp_us_html, schema_editor):
            updates['cmp_us_html'] = CMP_US_HTML
        if empty_needs_seed(page.cmp_them_html, schema_editor):
            updates['cmp_them_html'] = CMP_THEM_HTML
        for index, text in STAT_TEXTS.items():
            field_name = f'stat_{index}_text'
            if empty_needs_seed(getattr(page, field_name), schema_editor):
                updates[field_name] = text
        if updates:
            AdvantagesPage.objects.filter(pk=page.pk).update(**updates)

    HomePage = apps.get_model('content', 'HomePage')
    home = HomePage.objects.filter(pk=1).first()
    if home is not None:
        updates = {}
        for name, default in HOME_COPY_DEFAULTS.items():
            if empty_needs_seed(getattr(home, name), schema_editor):
                updates[name] = default
        if updates:
            HomePage.objects.filter(pk=home.pk).update(**updates)


def fill_article_layouts(apps, schema_editor):
    from src.blog.article_data import BY_SLUG

    Post = apps.get_model('blog', 'Post')
    for slug, payload in BY_SLUG.items():
        row = Post.objects.filter(slug=slug).first()
        if row is None or not json_needs_seed(row.layout, schema_editor):
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
        if empty_needs_seed(getattr(page, name, ''), schema_editor):
            updates[name] = text
    if updates:
        ServicesPage.objects.filter(pk=page.pk).update(**updates)


def _fill_blank_fields(model, row, mapping, schema_editor):
    names = {field.name for field in model._meta.fields}
    updates = {}
    for name, text in mapping.items():
        if name not in names or not empty_needs_seed(getattr(row, name, ''), schema_editor):
            continue
        updates[name] = text
    if updates:
        model.objects.filter(pk=row.pk).update(**updates)


HOME_SEO_MODE_COPY = {
    'seo_block_title_mode': 'Обмін валют в Україні',
    'seo_block_body_mode': (
        'Обмін21 — мережа обмінних пунктів. На сайті ви бачите актуальний курс, '
        'можете порахувати суму в калькуляторі та залишити заявку з фіксацією курсу. '
        'Розрахунок відбувається у відділенні.'
    ),
}


def fill_home_seo_mode(apps, schema_editor):
    """Заповнює порожні тексти SEO-блоку режиму. Повтор не перезаписує правки."""
    HomePage = apps.get_model('content', 'HomePage')
    home = HomePage.objects.filter(pk=1).first()
    if home is not None:
        _fill_blank_fields(HomePage, home, HOME_SEO_MODE_COPY, schema_editor)


def fill_articles_lead(apps, schema_editor):
    """Ставить лід статей лише якщо поле порожнє. Вступ сторінки послуг не чіпає."""
    from src.content.home_copy import SERVICES_MENTION_LEAD

    HomePage = apps.get_model('content', 'HomePage')
    home = HomePage.objects.filter(pk=1).first()
    if home is None:
        return
    _fill_blank_fields(HomePage, home, {'articles_lead': SERVICES_MENTION_LEAD}, schema_editor)


def fill_cmp_and_home_lead_mode(apps, schema_editor):
    """Заповнює порожні тексти порівняння і лідів режиму. Повтор не перезаписує правки."""
    from src.content.advantages_fields import CMP_MODE_COPY
    from src.content.home_copy import HOME_LEAD_MODE

    AdvantagesPage = apps.get_model('content', 'AdvantagesPage')
    page = AdvantagesPage.objects.filter(pk=1).first()
    if page is not None:
        _fill_blank_fields(AdvantagesPage, page, CMP_MODE_COPY, schema_editor)

    HomePage = apps.get_model('content', 'HomePage')
    home = HomePage.objects.filter(pk=1).first()
    if home is not None:
        _fill_blank_fields(HomePage, home, HOME_LEAD_MODE, schema_editor)


def noop_reverse(apps, schema_editor):
    return None
