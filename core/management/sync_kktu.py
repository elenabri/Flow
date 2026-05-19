# Ваше_приложение/management/commands/sync_kktu.py
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from ...services import VKORDService  # Пропишите правильный импорт вашего сервиса
from ...models import KktuCode       # Пропишите правильный импорт модели

class Command(BaseCommand):
    help = 'Синхронизация справочника ККТУ с ОРД VK'

    def handle(self, *args, **options):
        # ОРД работает асинхронно, запускаем через event loop
        asyncio.run(self.sync_data())

    async def sync_data(self):
        token = getattr(settings, "ORD_VK_TOKEN", "ВАШ_ТОКЕН")
        service = VKORDService(token=token)
        
        try:
            self.stdout.write("Запрос данных из ОРД VK...")
            # Предположим, ОРД возвращает список: [{"code": "10.20", "name": "Рыба"}, ...]
            # Структура может немного отличаться (например, быть вложенной). 
            # Настройте парсинг под реальный JSON ответа.
            kktu_list = await service.get_kktu_catalog() 
            
            count = 0
            for item in kktu_list:
                obj, created = KktuCode.objects.update_or_create(
                    code=item['code'],
                    defaults={
                        'name': item['name'],
                        'parent_code': item.get('parent_code')
                    }
                )
                if created:
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Успешно синхронизировано. Добавлено {count} новых кодов."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при синхронизации: {e}"))
