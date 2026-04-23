import os
import django
from django.core.asgi import get_asgi_application

# 1. Сначала устанавливаем переменную окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Инициализируем Django
django.setup()

# 3. Создаем базовое ASGI-приложение
django_asgi_app = get_asgi_application()

# 4. ТОЛЬКО ТЕПЕРЬ импортируем свои файлы (routing, consumers)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import core.routing 

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            core.routing.websocket_urlpatterns
        )
    ),
})
