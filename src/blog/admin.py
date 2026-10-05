from django.contrib import admin

from src.blog.models import Category, Post
from src.core.admin_mixins import ListUnfoldAdmin


@admin.register(Category)
class CategoryAdmin(ListUnfoldAdmin):
    list_display = ('name', 'slug', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(ListUnfoldAdmin):
    list_display = ('title', 'category', 'status', 'published_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    rich_fields = frozenset({'body', 'excerpt', 'faq'})
