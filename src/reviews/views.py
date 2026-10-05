from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from src.content.models import ReviewsPage
from src.reviews.forms import ReviewForm
from src.reviews.selectors import get_published_reviews


def review_list(request):
    form = ReviewForm()
    page = ReviewsPage.load()
    return render(request, 'reviews/review_list.html', {
        'reviews': get_published_reviews(),
        'form': form,
        'page': page,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.intro[:160],
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
        review.save()
        return render(request, 'partials/form_success.html', {
            'title': 'Дякуємо!',
            'message': 'Ваш відгук надіслано. Він зʼявиться на сайті після перевірки.',
        })
    return render(request, 'partials/modal_review.html', {'form': form}, status=422)
