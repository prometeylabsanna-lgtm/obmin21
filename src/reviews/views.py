from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from src.content.models import ReviewsPage
from src.core.exchange_mode import mode_meta
from src.core.notifications import notify_review
from src.reviews.forms import ReviewForm
from src.reviews.selectors import get_published_reviews


def review_list(request):
    form = ReviewForm()
    page = ReviewsPage.load()
    return render(request, 'reviews/review_list.html', {
        'reviews': get_published_reviews(),
        'form': form,
        'page': page,
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(
            page, 'seo_description', 'title', limit=None, request=request,
        ),
    })


@require_http_methods(['GET', 'POST'])
def review_submit(request):
    if request.method == 'GET':
        return render(request, 'partials/modal_review.html', {
            'form': ReviewForm(),
        })

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.is_published = False
        from src.content.models import HomePage
        review.home_page = HomePage.load()
        review.save()
        notify_review(review)
        return render(request, 'partials/form_success.html', {
            'title': 'Дякуємо!',
            'message': 'Ваш відгук надіслано. Він зʼявиться на сайті після перевірки.',
        })
    return render(request, 'partials/modal_review.html', {'form': form}, status=422)
