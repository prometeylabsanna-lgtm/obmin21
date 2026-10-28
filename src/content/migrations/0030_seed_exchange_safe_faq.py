from django.db import migrations


def seed_exchange_faq(apps, schema_editor):
    from src.content.faq_defaults import BASE_FAQ

    FaqItem = apps.get_model('content', 'FaqItem')
    HomePage = apps.get_model('content', 'HomePage')
    home_page = HomePage.objects.filter(pk=1).first()
    for offset, (question, answer) in enumerate(BASE_FAQ):
        FaqItem.objects.update_or_create(
            question=question,
            defaults={
                'answer': answer,
                'is_active': True,
                'exchange_safe': True,
                'sort_order': 900 + offset,
                'home_page': home_page,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0029_advantages_stat_1_text_mode'),
    ]

    operations = [
        migrations.RunPython(seed_exchange_faq, migrations.RunPython.noop),
    ]
