import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from whitenoise.asgi import WhiteNoiseASGI

# Импортируйте ваш файл routing из приложения core
# Убедитесь, что файл core/routing.py существует
try:
    from core.routing import websocket_urlpatterns
except ImportError:
    websocket_urlpatterns = []

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Инициализация Django ASGI приложения
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # WhiteNoiseASGI обрабатывает статику для HTTP запросов
    "http": WhiteNoiseASGI(django_asgi_app),
    
    # AuthMiddlewareStack обеспечивает доступ к user в сокетах
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
