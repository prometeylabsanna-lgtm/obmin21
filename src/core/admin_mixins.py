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
from src.core.plain_text import html_to_plain_legal, plain_text
from src.core.slugs import unique_slug

RICH_FIELD_NAMES = frozenset({
    'intro',
    'body',
    'seo_block_body',
    'answer',
    'faq',
    'short_desc',
})
COLOR_PREFIXES = ('color_', 'header_color_', 'footer_color_')
PLAIN_SKIP = frozenset({'color_bg', 'color_text', 'color_accent'})


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


def _strip_plain_fields(obj, rich_names):
    for field in obj._meta.fields:
        if field.name in rich_names or field.name in RICH_FIELD_NAMES:
            continue
        if field.name in PLAIN_SKIP or field.name.startswith(COLOR_PREFIXES):
            continue
        if field.get_internal_type() in ('CharField', 'SlugField', 'EmailField', 'URLField'):
            setattr(obj, field.name, plain_text(getattr(obj, field.name) or ''))


def _has_choices(db_field):
    return bool(getattr(db_field, 'choices', None))


class AutoSlugAdmin:
    compressed_fields = False
    slug_source = None

    def _slug_source(self):
        if self.slug_source == '':
            return ''
        names = {f.name for f in self.model._meta.fields}
        if 'slug' not in names:
            return ''
        if self.slug_source:
            return self.slug_source
        for candidate in ('title', 'code', 'name'):
            if candidate in names:
                return candidate
        return ''

    def _without_slug(self, fieldsets):
        cleaned = []
        for title, opts in fieldsets:
            fields = opts.get('fields')
            if not fields:
                cleaned.append((title, opts))
                continue
            cfg = dict(opts)
            cfg['fields'] = tuple(item for item in fields if item != 'slug')
            cleaned.append((title, cfg))
        return tuple(cleaned)

    def _ensure_slug(self, fieldsets):
        source = self._slug_source()
        placed = False
        cleaned = []
        for title, opts in fieldsets:
            fields = opts.get('fields')
            if not fields:
                cleaned.append((title, opts))
                continue
            next_fields = []
            for item in fields:
                if item == 'slug' and placed:
                    continue
                next_fields.append(item)
                if item == source:
                    next_fields.append('slug')
                    placed = True
                elif item == 'slug':
                    placed = True
            cfg = dict(opts)
            cfg['fields'] = tuple(next_fields)
            cleaned.append((title, cfg))
        if not placed and cleaned:
            title, opts = cleaned[0]
            cfg = dict(opts)
            cfg['fields'] = ('slug',) + tuple(cfg.get('fields') or ())
            cleaned[0] = (title, cfg)
        return tuple(cleaned)

    def _slug_fieldsets(self, fieldsets, obj):
        if not self._slug_source() or fieldsets is None:
            return fieldsets
        if not obj:
            return self._without_slug(fieldsets)
        return self._ensure_slug(fieldsets)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and self._slug_source() and 'slug' not in fields:
            fields.append('slug')
        return tuple(fields)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj or not self._slug_source():
            return fields
        return [name for name in fields if name != 'slug']

    def get_prepopulated_fields(self, request, obj=None):
        return {}

    def save_model(self, request, obj, form, change):
        source = self._slug_source()
        if source:
            obj.slug = unique_slug(obj, getattr(obj, source, ''))
        super().save_model(request, obj, form, change)


class SingletonUnfoldAdmin(AutoSlugAdmin, ModelAdmin):
    content_fields: tuple[str, ...] = ()
    content_fieldsets: tuple = ()
    style_fields: tuple[str, ...] = ('color_bg', 'color_text', 'color_accent')
    rich_fields: frozenset[str] = frozenset()
    plain_fields: frozenset[str] = frozenset()

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
        if self.content_fieldsets:
            tabs = []
            for title, opts in self.content_fieldsets:
                cfg = dict(opts)
                classes = list(cfg.get('classes', []))
                if 'tab' not in classes:
                    classes = ['tab', *classes]
                cfg['classes'] = classes
                tabs.append((title, cfg))
            if self.style_fields:
                tabs.append(
                    ('Оформлення', {'classes': ['tab'], 'fields': self.style_fields}),
                )
            return tuple(tabs)
        content = self.content_fields or tuple(
            f.name for f in self.model._meta.fields
            if f.name not in ('id', 'slug') and f.name not in self.style_fields
        )
        blocks = [('Контент', {'classes': ['tab'], 'fields': content})]
        if self.style_fields:
            blocks.append(
                ('Оформлення', {'classes': ['tab'], 'fields': self.style_fields}),
            )
        return self._slug_fieldsets(tuple(blocks), obj)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        name = db_field.name
        if name in self.plain_fields:
            if db_field.get_internal_type() == 'TextField':
                kwargs.setdefault(
                    'widget',
                    CmsAdminTextareaWidget(attrs={'rows': 18}),
                )
            return db_field.formfield(**kwargs)
        if name in self.rich_fields or name in RICH_FIELD_NAMES:
            kwargs['widget'] = CmsTinyMCE()
            return db_field.formfield(**kwargs)
        if name.startswith(COLOR_PREFIXES) or name in self.style_fields:
            kwargs['widget'] = CmsAdminColorWidget()
            return db_field.formfield(**kwargs)
        if isinstance(db_field, ImageField):
            kwargs['widget'] = _image_widget(self, db_field, request)
            return db_field.formfield(**kwargs)
        if _has_choices(db_field):
            return super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.get_internal_type() in ('CharField', 'URLField', 'EmailField'):
            kwargs.setdefault('widget', CmsAdminTextInputWidget())
        elif db_field.get_internal_type() == 'TextField':
            kwargs.setdefault('widget', CmsAdminTextareaWidget())
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        for name in self.plain_fields:
            if hasattr(obj, name):
                setattr(obj, name, html_to_plain_legal(getattr(obj, name) or ''))
        _strip_plain_fields(obj, self.rich_fields)
        super().save_model(request, obj, form, change)
        messages.success(request, 'Зміни успішно збережено!')


class ListUnfoldAdmin(AutoSlugAdmin, ModelAdmin):
    rich_fields: frozenset[str] = frozenset()
    search_help_text = 'Введіть запит для пошуку'
    list_filter_sheet = False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return self._slug_fieldsets(fieldsets, obj)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        name = db_field.name
        if name in self.rich_fields or name in RICH_FIELD_NAMES:
            kwargs['widget'] = CmsTinyMCE()
            return db_field.formfield(**kwargs)
        if isinstance(db_field, ImageField):
            kwargs['widget'] = _image_widget(self, db_field, request)
            return db_field.formfield(**kwargs)
        if _has_choices(db_field) or db_field.get_internal_type() == 'SlugField':
            return super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.get_internal_type() in ('CharField', 'URLField', 'EmailField'):
            kwargs.setdefault('widget', CmsAdminTextInputWidget())
        elif db_field.get_internal_type() == 'TextField':
            kwargs.setdefault('widget', CmsAdminTextareaWidget())
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        _strip_plain_fields(obj, self.rich_fields)
        super().save_model(request, obj, form, change)
