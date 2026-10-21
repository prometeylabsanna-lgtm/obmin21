from django.contrib import admin

from src.blog.models import Category, Post
from src.core.admin_mixins import ListUnfoldAdmin
from src.core.exchange_admin import ExchangeSafeListFilter


@admin.register(Category)
class CategoryAdmin(ListUnfoldAdmin):
    list_display = ('name', 'show_in_filter', 'sort_order')
    list_editable = ('show_in_filter', 'sort_order')
    fields = ('name', 'show_in_filter', 'sort_order')


@admin.register(Post)
class PostAdmin(ListUnfoldAdmin):
    list_display = ('title', 'exchange_safe', 'category', 'status', 'published_at')
    list_filter = (ExchangeSafeListFilter, 'status', 'category')
    ordering = ('-published_at', '-id')
    search_fields = ('title', 'body')
    search_help_text = 'Пошук за заголовком або текстом статті'
    date_hierarchy = 'published_at'
    filter_horizontal = ('related_posts',)
    rich_fields = frozenset({'body', 'excerpt', 'faq'})
    fieldsets = (
        ('Стаття', {
            'fields': (
                'exchange_safe',
                'title',
                'category',
                'status',
                'published_at',
                'cover',
                'excerpt',
                'body',
                'figure',
                'related_posts',
            ),
        }),
        ('Пошук', {
            'fields': ('seo_title', 'seo_description', 'faq'),
        }),
    )
