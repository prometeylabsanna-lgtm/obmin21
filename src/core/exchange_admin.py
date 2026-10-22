from django.contrib import admin

from src.core.exchange_fields import EXCHANGE_SAFE_HELP


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
        return display

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if not any(_is_exchange_safe_filter(item) for item in filters):
            filters.insert(0, ExchangeSafeListFilter)
        return filters

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'exchange_safe':
            kwargs['help_text'] = db_field.help_text or EXCHANGE_SAFE_HELP
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.action(description='Позначити як обмін', permissions=['change'])
    def mark_exchange_safe(self, request, queryset):
        count = queryset.update(exchange_safe=True)
        self.message_user(request, f'Позначено як обмін: {count}.')

    @admin.action(description='Зняти позначку', permissions=['change'])
    def clear_exchange_safe(self, request, queryset):
        count = queryset.update(exchange_safe=False)
        self.message_user(request, f'Позначку знято: {count}.')


def _is_exchange_safe_filter(item):
    if item is ExchangeSafeListFilter:
        return True
    return getattr(item, 'parameter_name', None) == 'exchange_safe'
