from django.contrib import admin
from unfold.admin import TabularInline

from src.core.admin_mixins import ListUnfoldAdmin
from src.network.models import Branch, City


class BranchInline(TabularInline):
    model = Branch
    extra = 0


@admin.register(City)
class CityAdmin(ListUnfoldAdmin):
    list_display = ('name', 'slug', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [BranchInline]


@admin.register(Branch)
class BranchAdmin(ListUnfoldAdmin):
    list_display = ('address', 'city', 'phone', 'is_active', 'sort_order')
    list_filter = ('city', 'is_active')
    search_fields = ('address', 'phone')
