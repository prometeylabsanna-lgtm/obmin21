from django.urls import path

from src.content import views

app_name = 'content'

urlpatterns = [
    path('posluhy/', views.services_list, name='services'),
    path('perevahy/', views.advantages_page, name='advantages'),
    path('kontakty/', views.contacts_page, name='contacts'),
    path('faq/', views.faq_page, name='faq'),
    path(
        'polityka-konfidentsiynosti/',
        views.privacy_page,
        name='privacy',
    ),
]
