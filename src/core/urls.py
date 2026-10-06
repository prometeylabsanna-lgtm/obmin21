from django.urls import path

from src.core import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('theme.css', views.theme_css, name='theme_css'),
    path('partials/rates/', views.rates_partial, name='rates_partial'),
    path('partials/quotes.json', views.quotes_json, name='quotes_json'),
    path('robots.txt', views.robots_txt, name='robots'),
    path('sitemap.xml', views.safe_sitemap, name='sitemap'),
]
