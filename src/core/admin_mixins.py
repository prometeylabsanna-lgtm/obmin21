from django.contrib import messages
from django.db.models import ImageField
from django.http import HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin

from src.core.admin_widgets import (
    CmsAdminColorWidget,
    CmsAdminImageWidget,
    CmsAdminTextInputWidget,
    CmsAdminTextareaWidget,
    CmsTinyMCE,
)
from src.core.image_fallbacks import image_fallback_url, image_preview_fit

RICH_FIELD_NAMES = frozenset({
    'intro',
    'body',
    'seo_block_body',
    'answer',
    'faq',
})
COLOR_PREFIXES = ('color_', 'header_color_', 'footer_color_')


def _instance_from_request(admin, request):
    match = getattr(request, 'resolver_match', None)
    object_id = match.kwargs.get('object_id') if match else None
    if not object_id:
        return None
    return admin.model.objects.filter(pk=object_id).first()


def _image_widget(admin, db_field, request):
    instance = _instance_from_request(admin, request)
    return CmsAdminImageWidget(
        fallback_url=image_fallback_url(db_field.name, instance),
        fit=image_preview_fit(db_field.name),
    )


class SingletonUnfoldAdmin(ModelAdmin):
    content_fields: tuple[str, ...] = ()
    style_fields: tuple[str, ...] = ('color_bg', 'color_text', 'color_accent')
    rich_fields: frozenset[str] = frozenset()

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = self.model.objects.get_or_create(pk=1)
        return HttpResponseRedirect(
            reverse(
                f'admin:{self.opts.app_label}_{self.opts.model_name}_change',
                args=[obj.pk],
            )
        )

    def get_fieldsets(self, request, obj=None):
        content = self.content_fields or tuple(
            f.name for f in self.model._meta.fields
            if f.name != 'id' and f.name not in self.style_fields
        )
        return (
            ('Контент', {'classes': ['tab'], 'fields': content}),
            ('Оформлення', {'classes': ['tab'], 'fields': self.style_fields}),
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        name = db_field.name
        if name in self.rich_fields or name in RICH_FIELD_NAMES:
            kwargs['widget'] = CmsTinyMCE()
            return db_field.formfield(**kwargs)
        if name.startswith(COLOR_PREFIXES) or name in self.style_fields:
            kwargs['widget'] = CmsAdminColorWidget()
            return db_field.formfield(**kwargs)
        if isinstance(db_field, ImageField):
            kwargs['widget'] = _image_widget(self, db_field, request)
            return db_field.formfield(**kwargs)
        if db_field.get_internal_type() in ('CharField', 'URLField', 'EmailField'):
            kwargs.setdefault('widget', CmsAdminTextInputWidget())
        elif db_field.get_internal_type() == 'TextField':
            kwargs.setdefault('widget', CmsAdminTextareaWidget())
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        messages.success(request, 'Зміни успішно збережено!')


class ListUnfoldAdmin(ModelAdmin):
    rich_fields: frozenset[str] = frozenset()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        name = db_field.name
        if name in self.rich_fields or name in RICH_FIELD_NAMES:
            kwargs['widget'] = CmsTinyMCE()
            return db_field.formfield(**kwargs)
        if isinstance(db_field, ImageField):
            kwargs['widget'] = _image_widget(self, db_field, request)
            return db_field.formfield(**kwargs)
        if db_field.get_internal_type() in ('CharField', 'URLField', 'EmailField', 'SlugField'):
            kwargs.setdefault('widget', CmsAdminTextInputWidget())
        elif db_field.get_internal_type() == 'TextField':
            kwargs.setdefault('widget', CmsAdminTextareaWidget())
        return super().formfield_for_dbfield(db_field, request, **kwargs)
