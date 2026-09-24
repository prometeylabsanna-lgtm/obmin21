from django.urls import path

from src.reviews import views

app_name = 'reviews'

urlpatterns = [
    path('vidhuky/', views.review_list, name='review_list'),
    path('htmx/vidhuk/', views.review_submit, name='review_submit'),
]
