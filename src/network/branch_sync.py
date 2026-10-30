"""Каталог відділень і ідемпотентне вирівнювання бази під нього.

Нові рядки не отримують телефон і графік. Існуючі телефон і графік
не змінюються. Порожній map_embed_url заповнюється з адреси (клієнт може
замінити в адмінці). Зайві відділення деактивуються, не видаляються.
"""

from collections import namedtuple
from urllib.parse import unquote_plus

from django.db import transaction

from src.network.models import default_map_embed_url, normalize_address

Point = namedtuple(
    'Point',
    ('city_name', 'slug', 'address', 'branch_name', 'city_sort', 'branch_sort'),
)

BRANCH_POINTS = (
    Point('Київ', 'kyiv', 'вул. Бульварно-Кудрявська, 32', '', 0, 0),
    Point('Харків', 'kharkiv', 'вул. Кацарська, 36/38', '', 1, 0),
    Point('Дніпро', 'dnipro', 'вул. Воскресенська, 4', '', 2, 0),
    Point('Одеса', 'odesa', 'вул. Рішельєвська, 54', '', 3, 0),
    Point('Львів', 'lviv', 'вул. Степана Бандери, 35', '', 4, 0),
    Point('Запоріжжя', 'zaporizhzhia', 'просп. Соборний, 153', '', 5, 0),
    Point('Миколаїв', 'mykolaiv', 'вул. Адміральська, 18', '', 6, 0),
    Point('Хмельницький', 'khmelnytskyi', 'вул. Подільська, 53', '', 7, 0),
    Point('Вінниця', 'vinnytsia', 'вул. Пирогова, 117', '', 8, 0),
    Point('Луцьк', 'lutsk', 'вул. Ковельська, 3/3', '', 9, 0),
    Point('Рівне', 'rivne', 'вул. Грушевського, 77', '', 10, 0),
    Point(
        'Івано-Франківськ',
        'ivano-frankivsk',
        'вул. Михайла Грушевського, 12',
        '',
        11,
        0,
    ),
    Point('Житомир', 'zhytomyr', 'вул. Київська, 41', '', 12, 0),
    Point('Чернігів', 'chernihiv', 'просп. Перемоги, 73', '', 13, 0),
    Point('Тернопіль', 'ternopil', 'вул. Руська, 18', '', 14, 0),
    Point('Черкаси', 'cherkasy', 'вул. Шевченка, 272', '', 15, 0),
    Point('Чернівці', 'chernivtsi', 'вул. Університетська, 26', '', 16, 0),
    Point(
        'Харків',
        'kharkiv',
        'метро Академіка Барабашова',
        'Барабашово',
        1,
        1,
    ),
)


def points_by_slug():
    grouped = {}
    order = []
    for point in BRANCH_POINTS:
        if point.slug not in grouped:
            grouped[point.slug] = []
            order.append(point.slug)
        grouped[point.slug].append(point)
    return [(slug, grouped[slug]) for slug in order]


def match_city_branches(existing, points):
    """Повертає (point → гілка, нові точки, зайві гілки).

    Спочатку збіг за адресою, потім за назвою точки, потім за порядком.
    """
    unused = list(existing)
    paired = {}
    for point in points:
        target = normalize_address(point.address)
        found = _take(unused, lambda branch: (
            normalize_address(getattr(branch, 'address', '')) == target
        ))
        if found is not None:
            paired[point] = found
    for point in points:
        if point in paired:
            continue
        label = normalize_address(point.branch_name)
        if not label:
            continue
        found = _take(unused, lambda branch: (
            normalize_address(getattr(branch, 'name', '')) == label
        ))
        if found is not None:
            paired[point] = found
    for point in points:
        if point in paired or not unused:
            continue
        paired[point] = unused.pop(0)
    creates = [point for point in points if point not in paired]
    return paired, creates, unused


def url_mentions_address(url, address):
    raw = str(url or '').strip()
    target = normalize_address(address)
    if not raw or not target:
        return False
    decoded = normalize_address(unquote_plus(raw))
    return target.casefold() in decoded.casefold()


class SyncReport:
    def __init__(self):
        self.lines = []
        self.gaps = []
        self.deactivated_branches = []
        self.deactivated_cities = []
        self.city_visibility = None
        self.branch_visibility = None

    @property
    def changed(self):
        return bool(self.lines)


def apply_branch_catalog(apps, dry_run=False):
    if dry_run:
        return _apply(apps, dry_run=True)
    with transaction.atomic():
        return _apply(apps, dry_run=False)


def _visibility(model):
    names = {field.name for field in model._meta.fields}
    for name in ('is_active', 'is_published'):
        if name in names:
            return name
    return None


def _find_city(cities, slug, name):
    for city in cities:
        if city.slug == slug:
            return city
    for city in cities:
        if (city.name or '') == name:
            return city
    return None


def _take(pool, predicate):
    for index, item in enumerate(pool):
        if predicate(item):
            return pool.pop(index)
    return None


def _save(obj, updates, dry_run):
    if not updates or dry_run:
        return
    for key, value in updates.items():
        setattr(obj, key, value)
    obj.save(update_fields=list(updates))


def _branch_updates(branch, point, field_names):
    updates = {}
    notes = []
    if branch.address != point.address:
        notes.append(f'адреса «{branch.address}» → «{point.address}»')
        updates['address'] = point.address
    current_name = getattr(branch, 'name', '') or ''
    if current_name != point.branch_name:
        notes.append(f'назва «{current_name}» → «{point.branch_name}»')
        updates['name'] = point.branch_name
    visibility = 'is_active' if 'is_active' in field_names else None
    if visibility and not getattr(branch, visibility):
        notes.append('активовано')
        updates[visibility] = True
    if branch.sort_order != point.branch_sort:
        notes.append(f'порядок {branch.sort_order} → {point.branch_sort}')
        updates['sort_order'] = point.branch_sort
    address_changed = (
        normalize_address(branch.address) != normalize_address(point.address)
    )
    if address_changed:
        if branch.lat is not None:
            updates['lat'] = None
        if branch.lng is not None:
            updates['lng'] = None
        if branch.lat is not None or branch.lng is not None:
            notes.append('скинуто координати')
        if 'coords_manual' in field_names and branch.coords_manual:
            updates['coords_manual'] = False
            notes.append('скинуто позначку ручних координат')
        if url_mentions_address(branch.map_url, branch.address):
            updates['map_url'] = ''
            notes.append('очищено map_url')
        if url_mentions_address(branch.map_embed_url, branch.address):
            updates['map_embed_url'] = ''
            notes.append('очищено map_embed_url')
    next_address = updates.get('address', branch.address)
    next_embed = updates.get('map_embed_url', branch.map_embed_url)
    if not str(next_embed or '').strip():
        filled = default_map_embed_url(next_address)
        if filled:
            updates['map_embed_url'] = filled
            notes.append('заповнено map_embed_url з адреси')
    return updates, notes


def _gap(city_name, branch_name, address, phone, hours, has_rows, lat, lng, map_url, map_embed):
    label = city_name
    if branch_name:
        label = f'{city_name} «{branch_name}»'
    parts = []
    if lat is None or lng is None:
        parts.append('координати: немає (карта за адресою)')
    else:
        parts.append('координати: є')
    if str(hours or '').strip() or has_rows:
        parts.append('графік: є')
    else:
        parts.append('графік: немає')
    if str(phone or '').strip():
        parts.append('телефон: є')
    else:
        parts.append('телефон: немає')
    if str(map_url or '').strip():
        parts.append('map_url: є')
    else:
        parts.append('map_url: немає (маршрут з адреси)')
    if str(map_embed or '').strip():
        parts.append('map_embed: є (має пріоритет над адресою)')
    else:
        parts.append('map_embed: немає (вбудована карта з адреси)')
    return f'{label} — {address}: ' + '; '.join(parts)


def _apply(apps, dry_run):
    City = apps.get_model('network', 'City')
    Branch = apps.get_model('network', 'Branch')
    branch_fields = {field.name for field in Branch._meta.fields}
    if 'name' not in branch_fields:
        raise ValueError('У відділення немає поля name. Спочатку виконайте migrate.')
    city_fields = {field.name for field in City._meta.fields}
    report = SyncReport()
    report.city_visibility = _visibility(City)
    report.branch_visibility = _visibility(Branch)
    try:
        Hours = apps.get_model('network', 'BranchOpeningHours')
    except LookupError:
        Hours = None
    hours_ids = set()
    if Hours is not None:
        hours_ids = set(Hours.objects.values_list('branch_id', flat=True))

    cities = list(City.objects.order_by('pk'))
    branches_by_city = {}
    for branch in Branch.objects.order_by('sort_order', 'id'):
        branches_by_city.setdefault(branch.city_id, []).append(branch)

    matched_city_ids = set()
    planned_active = {}
    for branch in Branch.objects.order_by('pk'):
        flag = report.branch_visibility
        planned_active[branch.pk] = bool(getattr(branch, flag)) if flag else True

    for slug, points in points_by_slug():
        sample = points[0]
        city = _find_city(cities, slug, sample.city_name)
        if city is None:
            report.lines.append(f'+ місто {sample.city_name} ({slug})')
            if not dry_run:
                kwargs = {
                    'name': sample.city_name,
                    'slug': slug,
                    'phone': '',
                    'is_active': True,
                    'sort_order': sample.city_sort,
                }
                if 'name_mode' in city_fields:
                    kwargs['name_mode'] = sample.city_name
                if report.city_visibility and report.city_visibility != 'is_active':
                    kwargs[report.city_visibility] = True
                city = City.objects.create(**kwargs)
                cities.append(city)
                matched_city_ids.add(city.pk)
            existing = []
        else:
            matched_city_ids.add(city.pk)
            city_updates = {}
            city_notes = []
            if city.name != sample.city_name:
                city_notes.append(f'назва «{city.name}» → «{sample.city_name}»')
                city_updates['name'] = sample.city_name
            if city.sort_order != sample.city_sort:
                city_notes.append(
                    f'порядок {city.sort_order} → {sample.city_sort}',
                )
                city_updates['sort_order'] = sample.city_sort
            if report.city_visibility and not getattr(city, report.city_visibility):
                city_notes.append('активовано')
                city_updates[report.city_visibility] = True
            if city_notes:
                report.lines.append(
                    f'~ місто {sample.city_name}: ' + '; '.join(city_notes),
                )
            _save(city, city_updates, dry_run)
            existing = list(branches_by_city.get(city.pk, []))

        paired, creates, leftover = match_city_branches(existing, points)
        for point in points:
            branch = paired.get(point)
            if branch is None:
                report.lines.append(
                    f'+ відділення {sample.city_name}'
                    f'{_suffix(point.branch_name)}: «{point.address}»'
                    ' (телефон і графік порожні)',
                )
                if city is not None and not dry_run:
                    kwargs = {
                        'city': city,
                        'address': point.address,
                        'name': point.branch_name,
                        'hours': '',
                        'phone': '',
                        'map_url': '',
                        'map_embed_url': default_map_embed_url(point.address),
                        'lat': None,
                        'lng': None,
                        'is_active': True,
                        'sort_order': point.branch_sort,
                    }
                    if 'coords_manual' in branch_fields:
                        kwargs['coords_manual'] = False
                    Branch.objects.create(**{
                        key: value
                        for key, value in kwargs.items()
                        if key == 'city' or key in branch_fields
                    })
                report.gaps.append(_gap(
                    point.city_name,
                    point.branch_name,
                    point.address,
                    '',
                    '',
                    False,
                    None,
                    None,
                    '',
                    '',
                ))
                continue
            updates, notes = _branch_updates(branch, point, branch_fields)
            if notes:
                report.lines.append(
                    f'~ відділення {sample.city_name}{_suffix(point.branch_name)}'
                    f' #{branch.pk}: ' + '; '.join(notes),
                )
            _save(branch, updates, dry_run)
            if report.branch_visibility:
                planned_active[branch.pk] = True
            state = {
                'phone': branch.phone,
                'hours': branch.hours,
                'lat': branch.lat,
                'lng': branch.lng,
                'map_url': branch.map_url,
                'map_embed_url': branch.map_embed_url,
            }
            state.update(updates)
            report.gaps.append(_gap(
                point.city_name,
                point.branch_name,
                point.address,
                state['phone'],
                state['hours'],
                branch.pk in hours_ids,
                state['lat'],
                state['lng'],
                state['map_url'],
                state['map_embed_url'],
            ))
        for branch in leftover:
            _deactivate_branch(branch, city, report, dry_run, planned_active)

    for city in cities:
        if city.pk in matched_city_ids:
            continue
        for branch in branches_by_city.get(city.pk, []):
            _deactivate_branch(branch, city, report, dry_run, planned_active)
        _hide_city_if_empty(city, branches_by_city, planned_active, report, dry_run)
    return report


def _suffix(branch_name):
    if branch_name:
        return f' «{branch_name}»'
    return ''


def _deactivate_branch(branch, city, report, dry_run, planned_active):
    flag = report.branch_visibility
    if flag is None:
        return
    if not getattr(branch, flag):
        planned_active[branch.pk] = False
        return
    city_name = city.name if city is not None else ''
    report.lines.append(
        f'- відділення {city_name} #{branch.pk} «{branch.address}»: '
        'деактивовано, не видалено',
    )
    report.deactivated_branches.append((branch.pk, city_name, branch.address))
    _save(branch, {flag: False}, dry_run)
    planned_active[branch.pk] = False


def _hide_city_if_empty(city, branches_by_city, planned_active, report, dry_run):
    flag = report.city_visibility
    if flag is None:
        return
    remaining = [
        branch
        for branch in branches_by_city.get(city.pk, [])
        if planned_active.get(branch.pk, False)
    ]
    if remaining:
        return
    if not getattr(city, flag):
        return
    report.lines.append(
        f'- місто {city.name} ({city.slug}): приховано, '
        'бо не лишилось активних відділень',
    )
    report.deactivated_cities.append((city.pk, city.name, city.slug))
    _save(city, {flag: False}, dry_run)
