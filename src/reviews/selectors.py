import random

from src.core.crypto_visibility import mentions_crypto, crypto_enabled
from src.reviews.models import Review


def get_published_reviews(limit=None):
    items = list(Review.objects.filter(is_published=True))
    if not crypto_enabled():
        items = [
            item for item in items
            if not mentions_crypto(f'{item.name} {item.text} {item.city_name}')
        ]
    random.shuffle(items)
    if limit is not None:
        return items[:limit]
    return items
