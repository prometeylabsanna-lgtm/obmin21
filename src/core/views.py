from django.shortcuts import render
from django.views.generic import TemplateView

from src.blog.selectors import get_published_posts
from src.content.models import AdvantageItem, HomePage, Service
from src.rates.models import RateBoard
from src.rates.selectors import get_quotes_for_city
from src.reviews.selectors import get_published_reviews


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        city = self.request.city
        board = self.request.GET.get('board', RateBoard.RETAIL)
        if board not in RateBoard.values:
            board = RateBoard.RETAIL
        rows, updated_at = get_quotes_for_city(city, board)
        ctx.update({
            'page': HomePage.load(),
            'rate_rows': rows,
            'rate_updated_at': updated_at,
            'active_board': board,
            'boards': RateBoard.choices,
            'services': Service.objects.filter(is_active=True)[:3],
            'advantage_items': AdvantageItem.objects.filter(is_active=True),
            'advantage_audiences': AdvantageItem.Audience.choices,
            'news_posts': list(get_published_posts()[:3]),
            'home_reviews': list(get_published_reviews()[:3]),
        })
        return ctx


def rates_partial(request):
    board = request.GET.get('board', RateBoard.RETAIL)
    if board not in RateBoard.values:
        board = RateBoard.RETAIL
    rows, updated_at = get_quotes_for_city(request.city, board)
    return render(request, 'partials/rates_table.html', {
        'rate_rows': rows,
        'rate_updated_at': updated_at,
        'active_board': board,
        'boards': RateBoard.choices,
        'hide_full_table_link': request.GET.get('hide_full') == '1',
    })


def robots_txt(request):
    return render(request, 'core/robots.txt', content_type='text/plain')


def page_not_found(request, exception):
    return render(request, 'core/404.html', status=404)
