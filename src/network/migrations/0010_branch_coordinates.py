from decimal import Decimal

from django.db import migrations

# DOUBTFUL (not applied):
# - vinnytsia 'вул. Соборна, 30, Вінниця' (geocoded only to street level)
# - poltava, sumy, ivano-frankivsk, kryvyi-rih, kropyvnytskyi:
#   address is the Kyiv placeholder 'вул. Хрещатик, 1, Київ'
#   (address does not belong to the city; not geocoded)
# Kyiv row is keyed by slug and is not applied to other cities.

COORDINATES = {
    ('kharkiv', 'вул. Сумська, 10, Харків'): (
        Decimal('49.994443'),
        Decimal('36.232961'),
    ),
    ('kyiv', 'вул. Хрещатик, 1, Київ'): (
        Decimal('50.451447'),
        Decimal('30.527762'),
    ),
    ('odesa', 'вул. Дерибасівська, 5, Одеса'): (
        Decimal('46.483374'),
        Decimal('30.743932'),
    ),
    ('dnipro', 'пр. Яворницького, 50, Дніпро'): (
        Decimal('48.464501'),
        Decimal('35.047435'),
    ),
    ('cherkasy', 'бул. Шевченка, 200, Черкаси'): (
        Decimal('49.446123'),
        Decimal('32.054766'),
    ),
    ('lviv', 'пл. Ринок, 12, Львів'): (
        Decimal('49.841236'),
        Decimal('24.032683'),
    ),
    ('zaporizhzhia', 'пр. Соборний, 100, Запоріжжя'): (
        Decimal('47.824068'),
        Decimal('35.168336'),
    ),
    ('mykolaiv', 'вул. Соборна, 8, Миколаїв'): (
        Decimal('46.968596'),
        Decimal('31.990872'),
    ),
    ('khmelnytskyi', 'вул. Проскурівська, 20, Хмельницький'): (
        Decimal('49.424528'),
        Decimal('26.983851'),
    ),
    ('rivne', 'вул. Соборна, 15, Рівне'): (
        Decimal('50.618734'),
        Decimal('26.254182'),
    ),
}


def apply_branch_coordinates(apps, schema_editor):
    """Оновлює lat/lng лише коли slug і адреса збігаються точно, а обидві координати NULL."""
    Branch = apps.get_model('network', 'Branch')
    for (slug, address), (lat, lng) in COORDINATES.items():
        Branch.objects.filter(
            city__slug=slug,
            address=address,
            lat__isnull=True,
            lng__isnull=True,
        ).update(lat=lat, lng=lng)


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0009_clear_placeholder_branch_coords'),
    ]

    operations = [
        migrations.RunPython(apply_branch_coordinates, migrations.RunPython.noop),
    ]
