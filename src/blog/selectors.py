from src.blog.models import Post


def get_published_posts():
    return Post.objects.filter(status=Post.Status.PUBLISHED).select_related('category')
