from django.db import migrations


def _mark_keys(html):
    if not html:
        return html
    return html.replace('<span>', '<span class="k">')


def forwards(apps, schema_editor):
    Page = apps.get_model('content', 'AdvantagesPage')
    for page in Page.objects.all():
        page.cmp_us_html = _mark_keys(page.cmp_us_html)
        page.cmp_them_html = _mark_keys(page.cmp_them_html)
        page.save(update_fields=['cmp_us_html', 'cmp_them_html'])


def backwards(apps, schema_editor):
    Page = apps.get_model('content', 'AdvantagesPage')
    for page in Page.objects.all():
        page.cmp_us_html = (page.cmp_us_html or '').replace('<span class="k">', '<span>')
        page.cmp_them_html = (page.cmp_them_html or '').replace('<span class="k">', '<span>')
        page.save(update_fields=['cmp_us_html', 'cmp_them_html'])


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0017_faq_reviews_page_copy'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
