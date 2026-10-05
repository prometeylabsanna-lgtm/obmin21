from django.shortcuts import get_object_or_404, render

from src.blog.models import Category, Post
from src.blog.selectors import get_published_posts
from src.core.breadcrumbs import safe_reverse, trail


def post_list(request, category_slug=None):
    qs = get_published_posts()
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        qs = qs.filter(category=category)
    try:
        limit = int(request.GET.get('limit', 6))
    except (TypeError, ValueError):
        limit = 6
    limit = max(6, min(limit, 60))
    posts = list(qs)
    featured = posts[0] if posts else None
    rest = posts[1:] if posts else []
    list_url = (
        safe_reverse('blog:category', category_slug=category.slug)
        if category
        else safe_reverse('blog:post_list')
    )
    context = {
        'featured': featured,
        'posts': rest[:limit],
        'has_more': len(rest) > limit,
        'next_limit': limit + 6,
        'list_url': list_url,
        'categories': Category.objects.all(),
        'active_category': category,
        'page_title': category.name if category else 'Блог',
    }
    if category:
        context['breadcrumb_items'] = trail(
            ('Блог', safe_reverse('blog:post_list')),
            (category.name, None),
        )
    if request.headers.get('HX-Request'):
        return render(request, 'partials/blog_list.html', context)
    return render(request, 'blog/post_list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(
        Post,
        slug=slug,
        status=Post.Status.PUBLISHED,
    )
    published = get_published_posts().exclude(pk=post.pk)
    related = list(published.filter(category=post.category)[:3])
    if len(related) < 3:
        related_ids = {item.pk for item in related}
        extras = published.exclude(pk__in=related_ids)[: 3 - len(related)]
        related.extend(extras)
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'related': related,
        'page_title': post.seo_title or post.title,
        'page_description': post.seo_description or post.excerpt[:160],
        'breadcrumb_items': trail(
            ('Блог', safe_reverse('blog:post_list')),
            (post.category.name, None),
        ),
    })
