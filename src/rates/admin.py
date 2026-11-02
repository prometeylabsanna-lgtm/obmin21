from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db.models import OuterRef, Subquery
from django.forms.widgets import HiddenInput
from django.template.response import TemplateResponse
from django.utils.http import urlencode

from src.core.admin_mixins import ListUnfoldAdmin
from src.core.exchange_admin import ExchangeSafeAdminMixin, ExchangeSafeListFilter
from src.rates.models import CurrencyPair, Quote, RateBoard


def _quote_board(request):
    board = request.GET.get('board') or request.session.get('quote_board')
    if board not in (RateBoard.RETAIL, RateBoard.CRYPTO):
        return RateBoard.RETAIL
    return board


@admin.register(CurrencyPair)
class CurrencyPairAdmin(ExchangeSafeAdminMixin, ListUnfoldAdmin):
    list_display = ('code', 'name', 'exchange_safe', 'slug', 'is_active', 'sort_order')
    list_filter = (ExchangeSafeListFilter,)
    list_editable = ('is_active', 'sort_order')
    search_fields = ('code', 'name')
    fields = (
        'exchange_safe',
        'code',
        'name',
        'base_code',
        'flag_image',
        'is_active',
        'sort_order',
        'intro',
        'intro_mode',
        'seo_title',
        'seo_title_mode',
        'seo_description',
        'seo_description_mode',
    )
    rich_fields = frozenset({'intro'})


class InheritsBaseFilter(admin.SimpleListFilter):
    title = 'базовий курс'
    parameter_name = 'inherits'

    def lookups(self, request, model_admin):
        return (
            ('base', 'Базовий'),
            ('yes', 'Наслідує'),
            ('no', 'Перевизначено'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'base':
            return queryset.filter(city__isnull=True)
        if self.value() == 'yes':
            return queryset.filter(city__isnull=False, inherits_base=True)
        if self.value() == 'no':
            return queryset.filter(city__isnull=False, inherits_base=False)
        return queryset


@admin.register(Quote)
class QuoteAdmin(ListUnfoldAdmin):
    list_display = (
        'pair',
        'city',
        'inheritance_state',
        'buy',
        'sell',
        'effective_buy',
        'effective_sell',
        'updated_at',
        'is_active',
    )
    list_filter = ('city', 'is_active', InheritsBaseFilter)
    list_editable = ('buy', 'sell', 'is_active')
    search_fields = ('pair__code',)
    fields = ('pair', 'city', 'buy', 'sell', 'inherits_base', 'is_active', 'board')
    actions = ('reset_to_base_rate', 'override_base_rate')
    list_before_template = 'admin/rates/quote_board_tabs.html'

    def get_queryset(self, request):
        base = Quote.objects.filter(
            pair_id=OuterRef('pair_id'),
            board=OuterRef('board'),
            city__isnull=True,
        )
        return (
            super()
            .get_queryset(request)
            .filter(board=_quote_board(request))
            .annotate(
                _base_buy=Subquery(base.values('buy')[:1]),
                _base_sell=Subquery(base.values('sell')[:1]),
            )
        )

    @admin.display(description='Зв’язок')
    def inheritance_state(self, obj):
        if not obj.city_id:
            return 'Базовий'
        if obj.inherits_base:
            return 'Наслідує'
        return 'Перевизначено'

    @admin.display(description='Купівля на сайті')
    def effective_buy(self, obj):
        return self._effective_side(obj, 'buy')

    @admin.display(description='Продаж на сайті')
    def effective_sell(self, obj):
        return self._effective_side(obj, 'sell')

    def _effective_side(self, obj, side):
        if obj.city_id and obj.inherits_base:
            value = getattr(obj, f'_base_{side}', None)
            if value is not None:
                return value
        return getattr(obj, side)

    @admin.action(description='Скинути до базового курсу')
    def reset_to_base_rate(self, request, queryset):
        return self._confirm_inherit(
            request,
            queryset,
            action='reset_to_base_rate',
            title='Скинути до базового курсу',
            intro=(
                'Вибрані курси міст читатимуть базовий курс. '
                'Їхні збережені числа лишаться в базі, на сайті буде база.'
            ),
            confirm_label='Скинути до базового курсу',
            apply=self._apply_reset,
            done='Скинуто до базового курсу: {count}.',
        )

    @admin.action(description='Перевизначити')
    def override_base_rate(self, request, queryset):
        return self._confirm_inherit(
            request,
            queryset,
            action='override_base_rate',
            title='Перевизначити курс міста',
            intro=(
                'Вибрані міста перестануть читати базу. '
                'У рядок запишеться курс, який зараз на сайті.'
            ),
            confirm_label='Перевизначити',
            apply=self._apply_override,
            done='Перевизначено: {count}.',
        )

    def _confirm_inherit(self, request, queryset, action, title, intro, confirm_label, apply, done):
        city_rows = queryset.filter(city__isnull=False)
        if request.POST.get('confirm') == 'yes':
            count = apply(city_rows)
            if count:
                self.message_user(request, done.format(count=count))
            else:
                self.message_user(
                    request,
                    'Серед вибраних немає міських курсів.',
                    level=messages.WARNING,
                )
            return None
        context = {
            **self.admin_site.each_context(request),
            'title': title,
            'intro': intro,
            'confirm_label': confirm_label,
            'rows': [
                f'{row.pair.code} — {row.city.name}'
                for row in city_rows.select_related('pair', 'city')
            ],
            'queryset': city_rows,
            'action_name': action,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
            'cancel_url': request.get_full_path(),
        }
        return TemplateResponse(
            request,
            'admin/rates/quote_inherit_confirm.html',
            context,
        )

    def _apply_reset(self, city_rows):
        ids = list(city_rows.values_list('pk', flat=True))
        if not ids:
            return 0
        return Quote.objects.filter(pk__in=ids).update(inherits_base=True)

    def _apply_override(self, city_rows):
        rows = list(city_rows)
        if not rows:
            return 0
        bases = {
            (row.pair_id, row.board): row
            for row in Quote.objects.filter(
                pair_id__in={row.pair_id for row in rows},
                board__in={row.board for row in rows},
                city__isnull=True,
            )
        }
        count = 0
        for row in rows:
            base = bases.get((row.pair_id, row.board))
            buy = base.buy if row.inherits_base and base is not None else row.buy
            sell = base.sell if row.inherits_base and base is not None else row.sell
            Quote.objects.filter(pk=row.pk).update(
                inherits_base=False,
                buy=buy,
                sell=sell,
            )
            count += 1
        return count

    def changelist_view(self, request, extra_context=None):
        board = _quote_board(request)
        request.session['quote_board'] = board
        query = request.GET.copy()
        extra_context = extra_context or {}
        extra_context['rate_board'] = board
        extra_context['rate_board_tabs'] = [
            {
                'value': RateBoard.RETAIL,
                'label': 'Готівка',
                'url': self._board_url(query, RateBoard.RETAIL),
            },
            {
                'value': RateBoard.CRYPTO,
                'label': 'Крипто',
                'url': self._board_url(query, RateBoard.CRYPTO),
            },
        ]
        return super().changelist_view(request, extra_context)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial['board'] = _quote_board(request)
        return initial

    def save_model(self, request, obj, form, change):
        if not change or not obj.board:
            obj.board = _quote_board(request)
        super().save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'board':
            kwargs['widget'] = HiddenInput()
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def _board_url(self, query, board):
        params = query.copy()
        params['board'] = board
        if 'p' in params:
            del params['p']
        encoded = urlencode(params, doseq=True)
        return f'?{encoded}' if encoded else f'?board={board}'
