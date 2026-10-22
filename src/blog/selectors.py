from django.db.models import F

from src.blog.models import Category, Post
from src.core.exchange_mode import exchange_only
from src.core.exchange_stopwords import matches_stop_words


def get_published_posts():
    return (
        Post.objects.visible()
        .filter(status=Post.Status.PUBLISHED)
        .select_related('category')
        .order_by(F('published_at').desc(nulls_last=True), '-id')
    )


def category_is_public(category, published=None):
    if category is None or not category.show_in_filter:
        return False
    posts = get_published_posts() if published is None else published
    if not posts.filter(category=category).exists():
        return False
    if exchange_only() and matches_stop_words(category.slug, category.name):
        return False
    return True


def visible_categories():
    published = get_published_posts()
    categories = Category.objects.filter(
        show_in_filter=True,
        pk__in=published.values('category_id'),
    )
    if not exchange_only():
        return categories
    public_ids = [
        category.pk
        for category in categories
        if category_is_public(category, published)
    ]
    return categories.filter(pk__in=public_ids)
