from django.urls import path

from src.network import views

app_name = 'network'

urlpatterns = [
    path('mista/', views.city_list, name='city_list'),
    path('mista/<slug:slug>/', views.city_detail, name='city_detail'),
    path('mista/<slug:slug>/obraty/', views.select_city_redirect, name='select_city'),
    path('htmx/set-city/', views.set_city, name='set_city'),
]
