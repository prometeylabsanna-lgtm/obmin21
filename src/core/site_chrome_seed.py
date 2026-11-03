"""Початкові пункти меню/підвалу — точна копія того, що було захардкоджено в шаблонах.

Сід ідемпотентний: створює записи лише якщо їх ще немає (жодних перезаписів правок адміна).
"""

HEADER_MENU = (
    ('Послуги', 'content:services'),
    ('Переваги', 'content:advantages'),
    ('FAQ', 'content:faq'),
    ('Блог', 'blog:post_list'),
    ('Контакти', 'content:contacts'),
)

FOOTER_COLUMNS = (
    ('Послуги', 'services', ()),
    ('Компанія', 'links', (
        ('Послуги', 'content:services'),
        ('Переваги', 'content:advantages'),
        ('FAQ', 'content:faq'),
        ('Відгуки', 'reviews:review_list'),
        ('Блог', 'blog:post_list'),
        ('Контакти', 'content:contacts'),
    )),
    ('Документи', 'links', (
        ('Політика конфіденційності', 'content:privacy'),
        ('Публічна оферта', 'content:offer'),
        ('Політика використання файлів cookie', 'content:cookies'),
    )),
)


def seed_site_chrome(apps=None):
    """Повертає (створено_пунктів_меню, створено_колонок)."""
    if apps is None:
        from src.core.models import FooterColumn, FooterLink, HeaderMenuItem
    else:
        HeaderMenuItem = apps.get_model('core', 'HeaderMenuItem')
        FooterColumn = apps.get_model('core', 'FooterColumn')
        FooterLink = apps.get_model('core', 'FooterLink')

    menu_created = 0
    if not HeaderMenuItem.objects.exists():
        for order, (label, page) in enumerate(HEADER_MENU, start=1):
            HeaderMenuItem.objects.create(
                settings_id=1, label=label, page=page, sort_order=order * 10,
            )
            menu_created += 1

    cols_created = 0
    if not FooterColumn.objects.exists():
        for order, (title, kind, links) in enumerate(FOOTER_COLUMNS, start=1):
            col = FooterColumn.objects.create(
                settings_id=1, title=title, kind=kind, sort_order=order * 10,
            )
            cols_created += 1
            for link_order, (label, page) in enumerate(links, start=1):
                FooterLink.objects.create(
                    column=col, label=label, page=page, sort_order=link_order * 10,
                )
    return menu_created, cols_created
