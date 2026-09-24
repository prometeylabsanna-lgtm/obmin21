from src.reviews.models import Review


def get_published_reviews():
    return Review.objects.filter(is_published=True)
