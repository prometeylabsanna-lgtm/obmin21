from django.db.models import F

from src.blog.models import Category, Post


def get_published_posts():
    return (
        Post.objects.visible()
        .filter(status=Post.Status.PUBLISHED)
        .select_related('category')
        .order_by(F('published_at').desc(nulls_last=True), '-id')
    )


def visible_categories():
    return Category.objects.filter(
        show_in_filter=True,
        pk__in=get_published_posts().values('category_id'),
    )
