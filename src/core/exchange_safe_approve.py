"""Затверджені exchange_safe для статей, відгуків і готівкових пар до UAH."""

APPROVED_POST_IDS = (8, 10, 12, 14, 15, 17, 2, 3, 4, 5, 7)
APPROVED_REVIEW_IDS = (1, 2, 3, 4, 5, 8, 10)
APPROVED_PAIR_SLUGS = (
    'usd-uah',
    'eur-uah',
    'gbp-uah',
    'pln-uah',
    'chf-uah',
    'cny-uah',
    'czk-uah',
    'cad-uah',
    'jpy-uah',
    'try-uah',
    'huf-uah',
    'sek-uah',
    'nok-uah',
    'dkk-uah',
    'aed-uah',
    'mdl-uah',
)


def mark_approved_exchange_safe(apps, schema_editor):
    _set_approved(apps, True)


def clear_approved_exchange_safe(apps, schema_editor):
    _set_approved(apps, False)


def _set_approved(apps, value):
    post = apps.get_model('blog', 'Post')
    review = apps.get_model('reviews', 'Review')
    pair = apps.get_model('rates', 'CurrencyPair')
    post.objects.filter(pk__in=APPROVED_POST_IDS).update(exchange_safe=value)
    review.objects.filter(pk__in=APPROVED_REVIEW_IDS).update(exchange_safe=value)
    pair.objects.filter(slug__in=APPROVED_PAIR_SLUGS).update(exchange_safe=value)
