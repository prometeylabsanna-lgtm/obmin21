from django.contrib import admin

from src.core.exchange_fields import EXCHANGE_SAFE_HELP
from src.core.exchange_mode import ExchangeVisibility

_CLASSIFY_FIELDS = ('exchange_visibility', 'kind', 'content_kind')


class ExchangeSafeListFilter(admin.SimpleListFilter):
    title = 'Режим лише обмін: так/ні'
    parameter_name = 'exchange_safe'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Так'),
            ('0', 'Ні'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == '1':
            return queryset.filter(exchange_safe=True)
        if value == '0':
            return queryset.filter(exchange_safe=False)
        return queryset


class ExchangeVisibilityListFilter(admin.SimpleListFilter):
    title = 'Видимість у режимі «Лише обмін»'
    parameter_name = 'exchange_visibility'

    def lookups(self, request, model_admin):
        return ExchangeVisibility.choices

    def queryset(self, request, queryset):
        value = self.value()
        if value in {ExchangeVisibility.AUTO, ExchangeVisibility.SHOW, ExchangeVisibility.HIDE}:
            return queryset.filter(exchange_visibility=value)
        return queryset


class ExchangeSafeAdminMixin:
    actions = (
        'mark_exchange_safe',
        'clear_exchange_safe',
        'delete_selected',
    )

    def get_list_display(self, request):
        display = list(super().get_list_display(request))
        if 'exchange_safe' not in display:
            display.append('exchange_safe')
        for name in _CLASSIFY_FIELDS:
            if name in _model_field_names(self.model) and name not in display:
                display.append(name)
        return display

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if not any(_is_exchange_safe_filter(item) for item in filters):
            filters.insert(0, ExchangeSafeListFilter)
        if (
            'exchange_visibility' in _model_field_names(self.model)
            and not any(_is_visibility_filter(item) for item in filters)
        ):
            filters.insert(0, ExchangeVisibilityListFilter)
        return filters

    def get_fieldsets(self, request, obj=None):
        return _with_exchange_fields(self.model, super().get_fieldsets(request, obj))

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if 'kind' in _model_field_names(self.model) and 'kind' not in readonly:
            readonly.append('kind')
        return tuple(readonly)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'exchange_safe':
            kwargs['help_text'] = db_field.help_text or EXCHANGE_SAFE_HELP
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.action(description='Позначити як обмін', permissions=['change'])
    def mark_exchange_safe(self, request, queryset):
        count = queryset.update(
            exchange_safe=True,
            exchange_visibility=ExchangeVisibility.SHOW,
        )
        self.message_user(request, f'Позначено як обмін: {count}.')

    @admin.action(description='Зняти позначку', permissions=['change'])
    def clear_exchange_safe(self, request, queryset):
        count = queryset.update(
            exchange_safe=False,
            exchange_visibility=ExchangeVisibility.AUTO,
        )
        self.message_user(request, f'Позначку знято: {count}.')


def _model_field_names(model):
    return {field.name for field in model._meta.concrete_fields}


def _with_exchange_fields(model, fieldsets):
    extra = [name for name in _CLASSIFY_FIELDS if name in _model_field_names(model)]
    if not extra:
        return fieldsets
    rebuilt = []
    inserted = False
    for title, opts in fieldsets:
        fields = list(opts.get('fields', ()))
        if not inserted and 'exchange_safe' in fields:
            index = fields.index('exchange_safe') + 1
            for name in extra:
                if name not in fields:
                    fields.insert(index, name)
                    index += 1
            inserted = True
        cfg = dict(opts)
        cfg['fields'] = tuple(fields)
        rebuilt.append((title, cfg))
    if not inserted and rebuilt:
        title, opts = rebuilt[0]
        fields = list(opts.get('fields', ()))
        for name in extra:
            if name not in fields:
                fields.insert(0, name)
        cfg = dict(opts)
        cfg['fields'] = tuple(fields)
        rebuilt[0] = (title, cfg)
    return tuple(rebuilt)


def _is_exchange_safe_filter(item):
    if item is ExchangeSafeListFilter:
        return True
    return getattr(item, 'parameter_name', None) == 'exchange_safe'


def _is_visibility_filter(item):
    if item is ExchangeVisibilityListFilter:
        return True
    return getattr(item, 'parameter_name', None) == 'exchange_visibility'
