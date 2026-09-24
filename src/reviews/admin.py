from django.contrib import admin
from django.utils import timezone

from src.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'city_name', 'is_published', 'created_at', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('name', 'text')
    actions = ['publish_reviews']

    @admin.action(description='Опублікувати')
    def publish_reviews(self, request, queryset):
        now = timezone.now()
        queryset.filter(is_published=False).update(
            is_published=True,
            published_at=now,
        )
