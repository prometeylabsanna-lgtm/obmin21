from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from src.blog.models import Post
from src.network.models import City
from src.rates.models import CurrencyPair


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return [
            'core:home',
            'rates:rates_page',
            'content:contacts',
            'content:services',
            'content:advantages',
            'blog:post_list',
            'reviews:review_list',
            'network:city_list',
            'content:privacy',
            'content:faq',
        ]

    def location(self, item):
        return reverse(item)


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('blog:post_detail', kwargs={'slug': obj.slug})


class PairSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return CurrencyPair.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('rates:pair_detail', kwargs={'slug': obj.slug})


class CitySitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return City.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('network:city_detail', kwargs={'slug': obj.slug})


sitemaps = {
    'static': StaticSitemap,
    'posts': PostSitemap,
    'pairs': PairSitemap,
    'cities': CitySitemap,
}
