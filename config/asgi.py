import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from whitenoise.asgi import WhiteNoiseASGI # Импортируем ASGI-версию WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Инициализируем стандартное ASGI приложение
django_asgi_app = get_asgi_application()

# Оборачиваем его в WhiteNoise, чтобы он отдавал статику до Channels
application = ProtocolTypeRouter({
    "http": WhiteNoiseASGI(django_asgi_app), 
    "websocket": AuthMiddlewareStack(
        URLRouter([
            # Здесь будут ваши пути для вебсокетов (routing.py)
        ])
    ),
})
