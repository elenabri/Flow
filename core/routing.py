# core/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Используем user_id, чтобы это совпадало с логикой в твоем consumers.py
    re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
