from django.contrib.sitemaps import Sitemap

from src.blog.models import Category
from src.blog.selectors import get_published_posts
from src.content.models import Service
from src.core.breadcrumbs import safe_reverse
from src.core.hidden_response import service_public_path
from src.network.models import City


def published_visible_posts():
    return get_published_posts().visible().exclude(slug='')


def public_services():
    return (
        Service.objects.filter(is_active=True)
        .visible()
        .exclude(slug='')
        .order_by('sort_order', 'id')
    )


def public_categories():
    return (
        Category.objects.filter(pk__in=published_visible_posts().values('category_id'))
        .exclude(slug='')
        .order_by('sort_order', 'name', 'id')
    )


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'

    def items(self):
        names = [
            'core:home',
            'rates:rates_page',
            'content:contacts',
            'content:services',
            'content:advantages',
            'blog:post_list',
            'reviews:review_list',
            'network:city_list',
            'content:privacy',
            'content:offer',
            'content:cookies',
            'content:faq',
        ]
        return [name for name in names if safe_reverse(name)]

    def location(self, item):
        return safe_reverse(item) or '/'


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return published_visible_posts()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return safe_reverse('blog:post_detail', slug=obj.slug) or '/'


def public_pairs():
    from src.rates.models import CurrencyPair

    return (
        CurrencyPair.objects.visible()
        .filter(is_active=True)
        .exclude(slug='')
        .order_by('sort_order', 'code')
    )


class PairSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return public_pairs()

    def location(self, obj):
        return safe_reverse('rates:pair_detail', slug=obj.slug) or '/'


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5
    protocol = 'https'

    def items(self):
        return public_categories()

    def location(self, obj):
        return safe_reverse('blog:category', category_slug=obj.slug) or '/'


class ServiceSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.4
    protocol = 'https'

    def items(self):
        return [
            service for service in public_services()
            if service_public_path(service.slug)
        ]

    def location(self, obj):
        return service_public_path(obj.slug) or '/'


class CitySitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        return City.objects.filter(is_active=True).exclude(slug='')

    def location(self, obj):
        return safe_reverse('network:city_detail', slug=obj.slug) or '/'


sitemaps = {
    'static': StaticSitemap,
    'posts': PostSitemap,
    'pairs': PairSitemap,
    'categories': CategorySitemap,
    'services': ServiceSitemap,
    'cities': CitySitemap,
}
