from django.db.models import F

from src.blog.models import Post
from src.core.crypto_visibility import visible_queryset


def get_published_posts():
    qs = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related('category')
        .order_by(F('published_at').desc(nulls_last=True), '-id')
    )
    return visible_queryset(
        qs,
        'title', 'slug', 'excerpt', 'body', 'faq',
        'seo_title', 'seo_description', 'category__name', 'category__slug',
    )
