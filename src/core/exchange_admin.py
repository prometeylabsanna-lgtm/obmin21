from django.contrib import admin


class ExchangeSafeListFilter(admin.SimpleListFilter):
    title = 'Режим лише обмін'
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
