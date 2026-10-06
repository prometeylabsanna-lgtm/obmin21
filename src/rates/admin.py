from django.contrib import admin
from django.forms.widgets import HiddenInput
from django.utils.http import urlencode

from src.core.admin_mixins import ListUnfoldAdmin
from src.rates.models import CurrencyPair, Quote, RateBoard


def _quote_board(request):
    board = request.GET.get('board') or request.session.get('quote_board')
    if board not in (RateBoard.RETAIL, RateBoard.CRYPTO):
        return RateBoard.RETAIL
    return board


@admin.register(CurrencyPair)
class CurrencyPairAdmin(ListUnfoldAdmin):
    list_display = ('code', 'name', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('code', 'name')
    fields = (
        'code',
        'name',
        'base_code',
        'flag_image',
        'is_active',
        'sort_order',
        'intro',
        'seo_title',
        'seo_description',
    )
    rich_fields = frozenset({'intro'})


@admin.register(Quote)
class QuoteAdmin(ListUnfoldAdmin):
    list_display = ('pair', 'city', 'buy', 'sell', 'updated_at', 'is_active')
    list_filter = ('city', 'is_active')
    list_editable = ('buy', 'sell', 'is_active')
    search_fields = ('pair__code',)
    fields = ('pair', 'city', 'buy', 'sell', 'is_active', 'board')
    list_before_template = 'admin/rates/quote_board_tabs.html'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(board=_quote_board(request))

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
