import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from asgiref.sync import sync_to_async

# Абсолютные импорты (замените 'core' на имя вашего Django-приложения, если оно другое)
from core.services import VKORDService  
from core.models import KktuCode       

class Command(BaseCommand):
    help = 'Синхронизация справочника ККТУ с ОРД VK'

    def handle(self, *args, **options):
        # ОРД работает асинхронно, безопасно запускаем event loop
        asyncio.run(self.sync_data())

    # Выносим синхронную работу с базой в отдельный метод
    def save_kktu_item(self, item):
        obj, created = KktuCode.objects.update_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'parent_code': item.get('parent_code')
            }
        )
        return created

    async def sync_data(self):
        token = getattr(settings, "ORD_VK_TOKEN", None)
        if not token or token == "ВАШ_ТОКЕН":
            self.stdout.write(self.style.ERROR("Ошибка: В settings.py не настроен ORD_VK_TOKEN"))
            return

        service = VKORDService(token=token)
        
        try:
            self.stdout.write("Запрос данных из ОРД VK...")
            response_data = await service.get_kktu_catalog() 
            
            # Архитектурная деталь: ОРД VK возвращает данные в виде словаря.
            # Если get_kktu_catalog() возвращает сырой ответ API, список обычно лежит в ['items'].
            # Делаем безопасную проверку структуры:
            if isinstance(response_data, dict) and 'items' in response_data:
                kktu_list = response_data['items']
            elif isinstance(response_data, list):
                kktu_list = response_data
            else:
                self.stdout.write(self.style.WARNING("Нетипичная структура ответа ОРД. Пробуем распарсить напрямую..."))
                kktu_list = response_data

            count = 0
            # Превращаем синхронный метод сохранения в асинхронную корутину
            async_save = sync_to_async(self.save_kktu_item, thread_sensitive=True)

            for item in kktu_list:
                # Проверяем, что в итерации есть нужные ключи, чтобы не упасть на полпути
                if not item or 'code' not in item or 'name' not in item:
                    continue
                
                # Вызываем безопасное сохранение в БД
                created = await async_save(item)
                if created:
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Успешно синхронизировано. Добавлено {count} новых кодов ККТУ."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при синхронизации: {e}"))
