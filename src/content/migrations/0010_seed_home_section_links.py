from django.db import migrations


STATS = (
    (0, '7K', '<p><b>Постійних клієнтів</b> — нам довіряють тисячі людей, які обирають нас для <b>швидкого та зручного обміну валют</b> і криптоактивів</p>'),
    (1, '20+', '<p><b>Відділень в Україні</b> — обмінюйте валюту <b>у зручному для вас відділенні</b> та отримуйте якісний сервіс</p>'),
    (2, '100%', '<p><b>Прозорість обміну</b> — жодних прихованих платежів: ви заздалегідь бачите <b>актуальний курс та умови операції</b></p>'),
    (3, '10+', '<p><b>Років досвіду</b> — понад 10 років ми працюємо у сфері обміну, забезпечуючи <b>стабільність, професійність та прозорі умови</b></p>'),
)


def seed_home_links(apps, schema_editor):
    HomePage = apps.get_model('content', 'HomePage')
    HomeStat = apps.get_model('content', 'HomeStat')
    FaqItem = apps.get_model('content', 'FaqItem')
    Service = apps.get_model('content', 'Service')
    Review = apps.get_model('reviews', 'Review')
    page, _ = HomePage.objects.get_or_create(pk=1)
    FaqItem.objects.filter(home_page__isnull=True).update(home_page=page)
    Service.objects.filter(home_page__isnull=True).update(home_page=page)
    Review.objects.filter(home_page__isnull=True).update(home_page=page)
    if not HomeStat.objects.exists():
        HomeStat.objects.bulk_create([
            HomeStat(page=page, sort_order=order, number=number, text=text)
            for order, number, text in STATS
        ])


def unseed(apps, schema_editor):
    HomeStat = apps.get_model('content', 'HomeStat')
    HomeStat.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0009_cms_page_sections'),
        ('reviews', '0003_cms_page_sections'),
    ]

    operations = [
        migrations.RunPython(seed_home_links, unseed),
    ]
