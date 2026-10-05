from django.shortcuts import get_object_or_404, render

from src.blog.models import Category, Post
from src.blog.selectors import get_published_posts
from src.content.models import BlogPage
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
    page = BlogPage.load()
    context = {
        'page': page,
        'featured': featured,
        'posts': rest[:limit],
        'has_more': len(rest) > limit,
        'next_limit': limit + 6,
        'list_url': list_url,
        'categories': Category.objects.all(),
        'active_category': category,
        'page_title': category.name if category else (page.seo_title or page.title),
        'page_description': page.seo_description or page.intro[:160],
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
    related = list(post.related_posts.filter(status=Post.Status.PUBLISHED)[:6])
    if not related:
        posts = list(get_published_posts())
        idx = next((i for i, item in enumerate(posts) if item.pk == post.pk), 0)
        related = []
        step = 1
        while len(related) < 6 and step < max(len(posts), 1):
            cand = posts[(idx + step) % len(posts)]
            if cand.pk != post.pk:
                related.append(cand)
            step += 1
    crumb = post.title
    layout = post.article_layout()
    if layout.get('h1b'):
        crumb = f"{layout['h1a']} {layout['h1b']}"
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'art': layout,
        'related': related,
        'page_title': post.seo_title or post.title,
        'page_description': post.seo_description or post.excerpt[:160],
        'breadcrumb_items': trail(
            ('Блог', safe_reverse('blog:post_list')),
            (crumb, None),
        ),
    })
