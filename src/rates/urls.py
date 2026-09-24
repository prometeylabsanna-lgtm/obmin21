from django.urls import path

from src.rates import views

app_name = 'rates'

urlpatterns = [
    path('kursy/', views.rates_page, name='rates_page'),
    path('<slug:slug>/', views.pair_detail, name='pair_detail'),
]
