from django.contrib.sitemaps import Sitemap

from src.blog.models import Post
from src.core.breadcrumbs import safe_reverse
from src.network.models import City
from src.rates.models import CurrencyPair


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
        return Post.objects.filter(status=Post.Status.PUBLISHED).exclude(slug='')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return safe_reverse('blog:post_detail', slug=obj.slug) or '/'


class PairSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return CurrencyPair.objects.filter(is_active=True).exclude(slug='')

    def location(self, obj):
        return safe_reverse('rates:pair_detail', slug=obj.slug) or '/'


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
    'cities': CitySitemap,
}
