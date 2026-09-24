from django.contrib import admin

from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    CitiesPage,
    ContactsPage,
    FaqItem,
    FaqPage,
    HomePage,
    PrivacyPage,
    RatesPage,
    Service,
    ServicesPage,
)


class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomePage)
class HomePageAdmin(SingletonAdmin):
    fieldsets = (
        ('SEO', {'fields': ('seo_title', 'seo_description')}),
        ('Банери', {'fields': ('banner_exchange', 'banner_service', 'banner_cta')}),
        ('CTA', {'fields': ('cta_title',)}),
        ('SEO-блок', {'fields': ('seo_block_title', 'seo_block_body')}),
    )


@admin.register(RatesPage)
class RatesPageAdmin(SingletonAdmin):
    pass


@admin.register(ServicesPage)
class ServicesPageAdmin(SingletonAdmin):
    pass


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(AdvantagesPage)
class AdvantagesPageAdmin(SingletonAdmin):
    pass


@admin.register(AdvantageItem)
class AdvantageItemAdmin(admin.ModelAdmin):
    list_display = ('text', 'audience', 'sort_order', 'is_active')
    list_filter = ('audience', 'is_active')
    list_editable = ('sort_order', 'is_active')


@admin.register(ContactsPage)
class ContactsPageAdmin(SingletonAdmin):
    pass


@admin.register(PrivacyPage)
class PrivacyPageAdmin(SingletonAdmin):
    pass


@admin.register(CitiesPage)
class CitiesPageAdmin(SingletonAdmin):
    pass


@admin.register(FaqPage)
class FaqPageAdmin(SingletonAdmin):
    pass


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('question', 'answer')
