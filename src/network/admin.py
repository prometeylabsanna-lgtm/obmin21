from django.contrib import admin

from src.network.models import Branch, City


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'phone', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [BranchInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'phone', 'is_active', 'sort_order')
    list_filter = ('city', 'is_active')
    search_fields = ('address', 'phone')
