from django.urls import path

from src.bot import views, web_views

app_name = 'bot'

urlpatterns = [
    path('telegram/webhook/', views.telegram_webhook, name='webhook'),
    path('htmx/chat/', web_views.chat_log, name='chat_log'),
    path('htmx/chat/send/', web_views.chat_send, name='chat_send'),
    path('htmx/chat/callback/', web_views.chat_callback, name='chat_callback'),
]
