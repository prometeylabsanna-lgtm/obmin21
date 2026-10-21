import random

from src.core.crypto_visibility import mentions_crypto
from src.core.exchange_mode import exchange_only
from src.reviews.models import Review


def get_published_reviews(limit=None):
    items = list(Review.objects.filter(is_published=True))
    if exchange_only():
        items = [
            item for item in items
            if not mentions_crypto(f'{item.name} {item.text} {item.city_name}')
        ]
    random.shuffle(items)
    if limit is not None:
        return items[:limit]
    return items
