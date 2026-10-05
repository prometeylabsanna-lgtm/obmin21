import random

from src.reviews.models import Review


def get_published_reviews(limit=None):
    items = list(Review.objects.filter(is_published=True))
    random.shuffle(items)
    if limit is not None:
        return items[:limit]
    return items
