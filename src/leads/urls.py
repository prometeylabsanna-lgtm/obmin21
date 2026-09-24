from django.urls import path

from src.leads import views

app_name = 'leads'

urlpatterns = [
    path('htmx/calc/', views.calc_modal, name='calc_modal'),
    path('htmx/zayavka/', views.exchange_request_modal, name='request_modal'),
    path('htmx/kontakt/', views.contact_submit, name='contact_submit'),
]
