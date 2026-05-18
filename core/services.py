import aiohttp # Используем асинхронную библиотеку, чтобы сайт не зависал
from django.conf import settings

async def send_telegram_message(recipient_tg_id, title, text):
    token = "8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k" # Рекомендую вынести в .env -> settings.TG_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Тот самый "чистый" формат: Тема жирным, ниже текст
    formatted_text = f"<b>{title}</b>\n\n{text}"
    
    payload = {
        "chat_id": recipient_tg_id,
        "text": formatted_text,
        "parse_mode": "HTML"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()

import requests
import logging

logger = logging.getLogger(__name__)

class VKORDService:
    """Сервис для прямой интеграции TubeFlow с API ОРД VK"""
    
    #BASE_URL = "https://api.ord.vk.com" # Или sandbox-api.ord.vk.com для песочницы
    
    BASE_URL = "https://sandbox-api.ord.vk.com" 
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def create_person(self, data):
        """Регистрация контрагента (Рекламодателя или Блогера)"""
        url = f"{self.BASE_URL}/v1/person"
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("external_id")
        raise Exception(f"Ошибка ОРД VK при создании контрагента: {response.text}")

    def create_pad(self, blogger_external_id, channel_url, channel_name):
        """Регистрация площадки (YouTube-канала)"""
        url = f"{self.BASE_URL}/v1/pad"
        payload = {
            "person_external_id": blogger_external_id,
            "type": "channel",
            "url": channel_url,
            "name": channel_name
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"Ошибка ОРД VK при регистрации площадки: {response.text}")

    def create_contract(self, advertiser_ext_id, blogger_ext_id):
        """Создание договора между Рекламодателем и Блогером"""
        import uuid
        contract_ext_id = f"cnt_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/contract"
        payload = {
            "external_id": contract_ext_id,
            "client_external_id": advertiser_ext_id,
            "contractor_external_id": blogger_ext_id,
            "type": "contract",
            "subject_type": "distribution", # Распространение рекламы
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code in [200, 201]:
            return contract_ext_id
        raise Exception(f"Ошибка ОРД VK при создании договора: {response.text}")

    def upload_media(self, file_object):
        """Загрузка ролика методом PUT"""
        import uuid
        media_ext_id = f"med_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/media/{media_ext_id}"
        
        # Меняем заголовок для отправки бинарного потока
        upload_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream"
        }
        
        response = requests.put(url, data=file_object.read(), headers=upload_headers)
        if response.status_code in [200, 201, 204]:
            return media_ext_id
        raise Exception(f"Ошибка ОРД VK при загрузке видео: {response.text}")

    def create_creative(self, contract_ext_id, channel_name, product_name, kktu_code, media_external_id, target_urls):
        """Регистрация креатива и получение долгожданного ERID"""
        import uuid
        creative_ext_id = f"crt_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/creative"
        
        payload = {
            "external_id": creative_ext_id,
            "contract_external_id": contract_ext_id,
            "type": "video",
            "name": f"Интеграция {channel_name} - {product_name}",
            "okveds": [kktu_code],
            "media_external_ids": [media_external_id],
            "target_urls": target_urls
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("erid", "ОШИБКА_ТОКЕНА")
        raise Exception(f"Ошибка ОРД VK при генерации ERID: {response.text}")

    def create_invoice(self, contract_ext_id, invoice_number, amount):
        """Регистрация акта/счета"""
        import uuid
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/invoice"
        
        payload = {
            "external_id": invoice_ext_id,
            "contract_external_id": contract_ext_id,
            "number": invoice_number,
            "amount": amount,
            "items": [{"contract_external_id": contract_ext_id, "amount": amount}]
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code in [200, 201]:
            return invoice_ext_id
        raise Exception(f"Ошибка ОРД VK при привязке акта: {response.text}")
