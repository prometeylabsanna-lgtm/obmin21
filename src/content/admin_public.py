from django.contrib import admin

from src.content.models import HomePage
from src.content.promo_slides import HomePromoSlide
from src.content.visit_steps import VisitSteps
from src.core.admin_mixins import ListUnfoldAdmin, SingletonUnfoldAdmin
from src.core.exchange_admin import ExchangeSafeAdminMixin


@admin.register(HomePromoSlide)
class HomePromoSlideAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = (
        'title',
        'sort_order',
        'is_active',
        'exchange_safe',
        'link_kind',
    )
    list_display_links = ('title',)
    list_editable = ('sort_order', 'is_active')
    ordering = ('sort_order', 'id')
    fields = (
        'title',
        'title_accent',
        'text',
        'button_label',
        'image',
        'image_path',
        'link_kind',
        'dot_label',
        'sort_order',
        'is_active',
        'exchange_safe',
        'code',
    )

    def save_model(self, request, obj, form, change):
        if not obj.page_id:
            obj.page = HomePage.load()
        super().save_model(request, obj, form, change)


@admin.register(VisitSteps)
class VisitStepsAdmin(SingletonUnfoldAdmin):
    style_fields = ()
    content_fields = (
        'title',
        'title_accent',
        'step_1_title',
        'step_1_text',
        'step_2_title',
        'step_2_text',
        'step_3_title',
        'step_3_text',
    )
