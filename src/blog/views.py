from django.core.paginator import Paginator
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
    paginator = Paginator(qs, 9)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list,
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
    related = get_published_posts().exclude(pk=post.pk).filter(category=post.category)[:3]
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
