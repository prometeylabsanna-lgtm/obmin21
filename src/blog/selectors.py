from django.db.models import F

from src.blog.models import Post


def get_published_posts():
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related('category')
        .order_by(F('published_at').desc(nulls_last=True), '-id')
    )
