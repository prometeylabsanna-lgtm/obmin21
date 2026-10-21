from django.contrib import admin
from django.utils import timezone

from src.core.admin_mixins import ListUnfoldAdmin
from src.core.exchange_admin import ExchangeSafeListFilter
from src.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(ListUnfoldAdmin):
    list_display = (
        'name',
        'exchange_safe',
        'city_name',
        'rating',
        'is_published',
        'created_at',
        'published_at',
    )
    list_filter = (ExchangeSafeListFilter, 'is_published', 'rating')
    search_fields = ('name', 'text')
    fields = (
        'exchange_safe',
        'name',
        'city_name',
        'rating',
        'text',
        'is_published',
        'published_at',
    )
    rich_fields = frozenset({'text'})

    @admin.action(description='Опублікувати на сайті')
    def publish_reviews(self, request, queryset):
        now = timezone.now()
        queryset.filter(is_published=False).update(
            is_published=True,
            published_at=now,
        )
