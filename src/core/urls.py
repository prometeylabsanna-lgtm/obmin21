from django.urls import path

from src.core import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('partials/rates/', views.rates_partial, name='rates_partial'),
    path('robots.txt', views.robots_txt, name='robots'),
]
