from django.urls import path

from src.blog import views

app_name = 'blog'

urlpatterns = [
    path('blog/', views.post_list, name='post_list'),
    path('blog/kategoriya/<slug:category_slug>/', views.post_list, name='category'),
    path('blog/<slug:slug>/', views.post_detail, name='post_detail'),
]
