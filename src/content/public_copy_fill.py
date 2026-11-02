"""Скидає автотексти, яких не було видно в шаблоні 45ac44c."""

FAQ_INTRO_SEED = (
    'Короткі відповіді на найчастіші питання про обмін валют у мережі Обмін21.'
)
SEO_BLOCK_BODY_SEED = (
    'Обмін21 — мережа обмінних пунктів. На сайті ви бачите актуальний курс, '
    'можете порахувати суму в калькуляторі та залишити заявку з фіксацією курсу. '
    'Розрахунок відбувається у відділенні.'
)
REVIEWS_INTRO_SEED = 'Що кажуть люди, які вже обмінювали валюту в Обмін21.'

_HOME = {
    'calc_kicker': ('Калькулятор',),
    'calc_lead': ('Дізнайтесь, скільки ви отримаєте та зафіксуйте курс онлайн',),
    'map_kicker': ('Відділення',),
    'why_kicker': ('Переваги',),
    'services_kicker': ('Послуги',),
    'faq_kicker': ('Відповіді',),
    'reviews_kicker': ('Відгуки',),
    'articles_kicker': ('Статті',),
    'seo_block_title': ('Обмін валют', 'Обмін валют в Україні'),
    'seo_block_body': (SEO_BLOCK_BODY_SEED,),
}
_PAGES = (
    ('ContactsPage', {'branches_kicker': ('Відділення',)}),
    ('AdvantagesPage', {
        'hero_kicker': ('Переваги',),
        'stats_kicker': ('Цифри',),
        'why_kicker': ('Чому ми',),
        'why_kicker_mode': ('Чому ми',),
        'cmp_kicker': ('Порівняння',),
        'cmp_kicker_mode': ('Порівняння',),
    }),
    ('FaqPage', {
        'kicker': ('Відповіді',),
        'intro': (FAQ_INTRO_SEED,),
    }),
    ('ReviewsPage', {
        'kicker': ('Відгуки',),
        'intro': (REVIEWS_INTRO_SEED,),
    }),
)


def _clear(model, mapping):
    row = model.objects.filter(pk=1).first()
    if row is None:
        return
    updates = []
    for name, legacy in mapping.items():
        if not hasattr(row, name):
            continue
        current = getattr(row, name, '') or ''
        if not isinstance(current, str):
            continue
        if current.strip() not in legacy:
            continue
        setattr(row, name, '')
        updates.append(name)
    if updates:
        row.save(update_fields=updates)


def clear_unseen_public_copy(apps, schema_editor):
    from src.core.deploy_seed import migration_context

    if not migration_context(schema_editor):
        return
    home = apps.get_model('content', 'HomePage')
    _clear(home, _HOME)
    for model_name, mapping in _PAGES:
        _clear(apps.get_model('content', model_name), mapping)
