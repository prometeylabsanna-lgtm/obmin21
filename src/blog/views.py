from django.core.exceptions import FieldDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from src.blog.models import Category, Post
from src.blog.selectors import category_is_public, get_published_posts, visible_categories
from src.content.models import BlogPage
from src.core.breadcrumbs import safe_reverse, trail
from src.core.exchange_mode import exchange_only, mode_meta, mode_text, raise_hidden


def _related_posts(post):
    candidates = list(
        post.related_posts.filter(status=Post.Status.PUBLISHED)[:12]
    )
    visible_ids = set()
    if candidates:
        visible_ids = set(
            Post.objects.visible()
            .filter(pk__in=[item.pk for item in candidates])
            .values_list('pk', flat=True)
        )
    related = [item for item in candidates if item.pk in visible_ids][:6]
    if related:
        return related
    posts = list(get_published_posts())
    idx = next((i for i, item in enumerate(posts) if item.pk == post.pk), 0)
    related = []
    step = 1
    total = max(len(posts), 1)
    while len(related) < 6 and step < total:
        cand = posts[(idx + step) % len(posts)]
        if cand.pk != post.pk:
            related.append(cand)
        step += 1
    return related


def _model_text(obj, field):
    meta = getattr(obj, '_meta', None)
    get_field = getattr(meta, 'get_field', None)
    if not callable(get_field):
        return ''
    try:
        get_field(field)
    except FieldDoesNotExist:
        return ''
    return ' '.join(str(getattr(obj, field, '') or '').split())


def category_page_copy(category, request):
    """H1, title і description рубрики. seo_* якщо поле є, інакше шаблон з назвою."""
    name = ' '.join(str(getattr(category, 'name', '') or '').split())
    if exchange_only(request):
        title = _model_text(category, 'seo_title_mode')
        description = _model_text(category, 'seo_description_mode')
    else:
        title = _model_text(category, 'seo_title')
        description = _model_text(category, 'seo_description')
    if not title:
        title = name
    if not description and name:
        description = f'Статті рубрики {name}.'
    return {
        'heading': name or title,
        'title': title,
        'description': description,
    }


def post_list(request, category_slug=None):
    qs = get_published_posts()
    category = None
    if category_slug:
        category = get_object_or_404(
            Category,
            slug=category_slug,
            show_in_filter=True,
        )
        if not category_is_public(category, qs):
            if exchange_only():
                raise_hidden()
            raise Http404
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
    copy = category_page_copy(category, request) if category else None
    context = {
        'page': page,
        'featured': featured,
        'posts': rest[:limit],
        'has_more': len(rest) > limit,
        'next_limit': limit + 6,
        'list_url': list_url,
        'categories': visible_categories(),
        'active_category': category,
        'category_heading': copy['heading'] if copy else '',
        'page_title': (
            copy['title']
            if copy
            else mode_meta(page, 'seo_title', 'title', limit=None, request=request)
        ),
        'page_description': (
            copy['description']
            if copy
            else mode_meta(page, 'seo_description', 'intro', request=request)
        ),
    }
    if category:
        context['breadcrumb_items'] = trail(
            ('Блог', safe_reverse('blog:post_list')),
            (category.name, None),
        )
    if request.headers.get('HX-Request'):
        return render(request, 'partials/blog_list.html', context)
    return render(request, 'blog/post_list.html', context)


def _layout_mode(post, layout, request):
    if not exchange_only(request):
        return layout
    return _mode_value(post, layout, request, None)


def _mode_value(post, value, request, key):
    if isinstance(value, dict):
        return {
            name: _mode_value(post, item, request, name)
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [_mode_value(post, item, request, None) for item in value]
    if key and hasattr(post, f'{key}_mode'):
        return mode_text(post, key, request)
    if isinstance(value, str):
        return ''
    return None


def _article_art(post, request):
    layout = post.article_layout()
    return {
        **layout,
        'layout': layout,
        'layout_mode': _layout_mode(post, layout, request),
    }


def post_detail(request, slug):
    published = Post.objects.filter(slug=slug, status=Post.Status.PUBLISHED)
    post = published.visible().first()
    if post is None:
        if exchange_only() and published.exists():
            raise_hidden()
        raise Http404
    art = _article_art(post, request)
    shown = art['layout_mode']
    if shown.get('h1b'):
        crumb = f"{shown['h1a']} {shown['h1b']}"
    else:
        crumb = mode_text(post, 'title', request)
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'art': art,
        'related': _related_posts(post),
        'page_title': mode_meta(post, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(post, 'seo_description', 'excerpt', request=request),
        'breadcrumb_items': trail(
            ('Блог', safe_reverse('blog:post_list')),
            (crumb, None),
        ),
    })
