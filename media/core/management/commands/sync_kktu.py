from django.core.management.base import BaseCommand
from core.models import KktuCode
from core.services import VKORDService
from django.conf import settings

class Command(BaseCommand):
    help = 'Синхронизация справочника ККТУ с API VK'

    def handle(self, *args, **kwargs):
        service = VKORDService(token=settings.VK_ORD_TOKEN)
        # Получаем данные порциями
        data = service.get_kktu_dict(limit=1000)
        items = data.get('items', [])
        
        for item in items:
            KktuCode.objects.update_or_create(
                code=item['code'],
                defaults={'name': item['name'], 'is_active': True}
            )
        self.stdout.write(f"Загружено {len(items)} кодов ККТУ")
