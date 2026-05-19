from django.core.management.base import BaseCommand
from django.conf import settings
from core.services import VKORDService  
from core.models import KktuCode       

class Command(BaseCommand):
    help = 'Синхронизация справочника ККТУ с ОРД VK (Словари v1)'

    def handle(self, *args, **options):
        token = getattr(settings, "ORD_VK_TOKEN", None)
        if not token or token == "ВАШ_ТОКЕН":
            self.stdout.write(self.style.ERROR("Ошибка: В settings.py не настроен ORD_VK_TOKEN"))
            return

        service = VKORDService(token=token)
        
        try:
            self.stdout.write("Запрос справочника ККТУ из ОРД VK (v1/dict)...")
            response_data = service.get_kktu_catalog() 
            
            # Читаем массив элементов строго из ключа 'items'
            kktu_list = response_data.get('items', [])

            if not kktu_list:
                self.stdout.write(self.style.WARNING("Предупреждение: ОРД вернул пустой список ККТУ."))
                return

            count = 0
            for item in kktu_list:
                if not item or 'code' not in item or 'name' not in item:
                    continue
                
                # Записываем или обновляем данные в локальной БД
                obj, created = KktuCode.objects.update_or_create(
                    code=item['code'],
                    defaults={
                        'name': item['name']
                    }
                )
                if created:
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Синхронизация завершена успешно! Добавлено {count} новых кодов ККТУ."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при синхронизации: {e}"))
