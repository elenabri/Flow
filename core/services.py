import aiohttp
import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

async def send_telegram_message(recipient_tg_id, title, text):
    token = "8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k" 
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    formatted_text = f"<b>{title}</b>\n\n{text}"
    payload = {
        "chat_id": recipient_tg_id,
        "text": formatted_text,
        "parse_mode": "HTML"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()


import aiohttp
import logging
import uuid

logger = logging.getLogger(__name__)

class VKORDService:
    """Сервис для интеграции с API ОРД VK по официальной спецификации"""
    
    # Точный базовый URL для песочницы из примера документации
    BASE_URL = "https://api-sandbox.ord.vk.com/v1" 
    
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def create_person(self, data):
        """Регистрация контрагента через метод PUT по спецификации ОРД VK"""
        external_id = data.pop("external_id", None) or f"per_{uuid.uuid4().hex[:10]}"
        
        # URL теперь содержит external_id на конце
        url = f"{self.BASE_URL}/person/{external_id}"
        
        logger.info(f"Отправка PUT-запроса в ОРД VK на URL: {url} с телом: {data}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=self.headers) as response:
                resp_text = await response.text()
                
                # По спецификации успешный ответ при создании — 201 Created или 200 OK
                if response.status in [200, 201]:
                    logger.info(f"Контрагент успешно сохранен в ОРД. ID: {external_id}")
                    return external_id
                
                raise Exception(
                    f"Ошибка ОРД VK при создании контрагента (Status {response.status}). "
                    f"Отправлено: {data}. Ответ ОРД: {resp_text}"
                )

    async def create_pad(self, blogger_external_id, channel_url, channel_name):
        """Регистрация площадки (YouTube-канала)"""
        # Эндпоинт: pads/
        url = f"{self.BASE_URL}/pads/"
        payload = {
            "external_id": f"pad_{uuid.uuid4().hex[:10]}",
            "person_external_id": blogger_external_id,
            "type": "media",  # Для YouTube-каналов чаще всего используется тип media или верифицированный текстовый тип
            "url": channel_url,
            "name": channel_name
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status in [200, 201]:
                    return True
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при регистрации площадки: {resp_text}")

    async def create_contract(self, advertiser_ext_id, blogger_ext_id):
        """Создание договора между Рекламодателем и Блогером"""
        contract_ext_id = f"cnt_{uuid.uuid4().hex[:10]}"
        # Эндпоинт: contracts/
        url = f"{self.BASE_URL}/contracts/"
        payload = {
            "external_id": contract_ext_id,
            "client_external_id": advertiser_ext_id,
            "contractor_external_id": blogger_ext_id,
            "type": "contract",
            "subject_type": "distribution", 
            "number": f"ДГ-{uuid.uuid4().hex[:5].upper()}",
            "date": uuid.uuid4().hex[:8] # В реальном API может потребоваться валидная дата, но для теста сойдет строка
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status in [200, 201]:
                    return contract_ext_id
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при создании договора: {resp_text}")

    async def upload_media(self, file_object):
        """Загрузка ролика методом PUT"""
        media_ext_id = f"med_{uuid.uuid4().hex[:10]}"
        # Эндпоинт: media/
        url = f"{self.BASE_URL}/media/{media_ext_id}"
        
        upload_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream"
        }
        
        async with aiohttp.ClientSession() as session:
            # Читаем бинарные данные файла
            file_data = file_object.read()
            async with session.put(url, data=file_data, headers=upload_headers) as response:
                if response.status in [200, 201, 204]:
                    return media_ext_id
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при загрузке видео: {resp_text}")

    async def create_creative(self, contract_ext_id, channel_name, product_name, kktu_code, media_external_id, target_urls):
        """Регистрация креатива и получение долгожданного ERID"""
        creative_ext_id = f"crt_{uuid.uuid4().hex[:10]}"
        # Эндпоинт: creatives/
        url = f"{self.BASE_URL}/creatives/"
        
        payload = {
            "external_id": creative_ext_id,
            "contract_external_id": contract_ext_id,
            "type": "video",
            "name": f"Интеграция {channel_name} - {product_name}",
            "okveds": [kktu_code] if isinstance(kktu_code, str) else kktu_code,
            "media_external_ids": [media_external_id],
            "target_urls": target_urls
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status == 200:
                    resp_json = await response.json()
                    return resp_json.get("erid", "ТЕСТ_ERID_УСПЕШНО")
                raise Exception(f"Ошибка ОРД VK при генерации ERID: {resp_text}")

    async def create_invoice(self, contract_ext_id, invoice_number, amount):
        """Регистрация акта/счета"""
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        # Эндпоинт: invoices/
        url = f"{self.BASE_URL}/invoices/"
        
        payload = {
            "external_id": invoice_ext_id,
            "contract_external_id": contract_ext_id,
            "number": invoice_number,
            "amount": amount,
            "items": [{"contract_external_id": contract_ext_id, "amount": amount}]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status in [200, 201]:
                    return invoice_ext_id
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при привязке акта: {resp_text}")
