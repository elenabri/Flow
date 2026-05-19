import json
import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import KktuCode

def load_data():
    with open('kktu_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for item in data:
        KktuCode.objects.update_or_create(
            code=item['code'],
            defaults={'name': item['name'], 'is_active': True}
        )
    print(f"Успешно загружено {len(data)} категорий!")

if __name__ == "__main__":
    load_data()
