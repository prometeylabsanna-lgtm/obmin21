from django.utils.text import slugify as django_slugify

_UA = str.maketrans({
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e',
    'є': 'ye', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'i', 'й': 'i',
    'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
    'ы': 'y', 'э': 'e', 'ъ': '',
})


def latin_slug(value: str, max_length: int = 80) -> str:
    raw = (value or '').strip().lower().translate(_UA)
    slug = django_slugify(raw)[:max_length].strip('-')
    return slug or 'item'


def unique_slug(instance, source_value: str, field_name: str = 'slug') -> str:
    current = getattr(instance, field_name, '') or ''
    if current:
        return current
    field = instance._meta.get_field(field_name)
    max_length = getattr(field, 'max_length', None) or 80
    base = latin_slug(source_value, max_length)
    slug = base
    model = instance.__class__
    n = 2
    qs = model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{field_name: slug}).exists():
        suffix = f'-{n}'
        slug = f'{base[:max_length - len(suffix)]}{suffix}'
        n += 1
    return slug
