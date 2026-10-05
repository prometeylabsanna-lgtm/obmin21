from django.urls import path

from src.bot import views

app_name = 'bot'

urlpatterns = [
    path('telegram/webhook/', views.telegram_webhook, name='webhook'),
]
