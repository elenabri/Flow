import logging
import uuid
import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)

async def send_telegram_message(recipient_tg_id, title, text):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        logger.error("Отмена отправки TG: Токен TELEGRAM_BOT_TOKEN не обнаружен в settings.py")
        return None
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    formatted_text = f"<b>{title}</b>\n\n{text}"
    payload = {
        "chat_id": recipient_tg_id,
        "text": formatted_text,
        "parse_mode": "HTML"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                return await response.json()
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
        return None


class VKORDService:
    """Сервис для интеграции с API ОРД VK по официальной спецификации"""
    
    BASE_URL = "https://api-sandbox.ord.vk.com" 
    
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def create_person(self, data):
        """Регистрация контрагента через метод PUT (v1)"""
        external_id = data.pop("external_id", None) or f"per_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/person/{external_id}"
        
        logger.info(f"Отправка PUT контрагента в ОРД VK v1 на URL: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status in [200, 201]:
                    logger.info(f"Контрагент успешно сохранен в ОРД. ID: {external_id}")
                    return external_id
                
                raise Exception(f"Ошибка ОРД VK при создании контрагента ({response.status}): {resp_text}")

    async def create_pad(self, blogger_external_id, channel_url, channel_name):
        """Регистрация площадки (v1)"""
        pad_id = f"pad_{uuid.uuid4().hex[:10]}"
        # Рекомендуемый подход через PUT для предотвращения дублей
        url = f"{self.BASE_URL}/v1/pad/{pad_id}"
        payload = {
            "person_external_id": blogger_external_id,
            "type": "media",  
            "url": channel_url,
            "name": channel_name
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=self.headers) as response:
                if response.status in [200, 201]:
                    return pad_id
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при регистрации площадки ({response.status}): {resp_text}")

    async def create_contract(self, contract_ext_id, payload):
        """Создание договора оказания услуг методом PUT (v1)"""
        url = f"{self.BASE_URL}/v1/contract/{contract_ext_id}"
        logger.info(f"Отправка PUT договора в ОРД VK v1 на URL: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status in [200, 201]:
                    logger.info(f"Договор успешно зарегистрирован. ID: {contract_ext_id}")
                    return contract_ext_id
                
                raise Exception(f"Ошибка ОРД VK при создании договора ({response.status}): {resp_text}")

    async def upload_media(self, video_file):
        """Загрузка медиафайла методом PUT (v1)"""
        media_external_id = f"med_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/media/{media_external_id}"
        
        data = aiohttp.FormData()
        file_bytes = video_file.read()
        data.add_field('media_file', file_bytes, filename=video_file.name)
        
        upload_headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
        
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data, headers=upload_headers) as response:
                resp_text = await response.text()
                if response.status in [200, 201]:
                    logger.info(f"Медиафайл успешно загружен. ID: {media_external_id}")
                    return media_external_id
                
                raise Exception(f"Ошибка ОРД VK при загрузке видео ({response.status}): {resp_text}")
    async def get_kktu_catalog(self):
        """Получение актуального справочника ККТУ из ОРД VK (v1)"""
        url = f"{self.BASE_URL}/v1/kktu"
        logger.info(f"Запрос справочника ККТУ из ОРД VK на URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                resp_text = await response.text()
                raise Exception(f"Не удалось получить справочник ККТУ ({response.status}): {resp_text}")

    async def create_creative(self, creative_ext_id, payload):
        """Создание креатива методом PUT (v3)"""
        url = f"{self.BASE_URL}/v3/creative/{creative_ext_id}"
        logger.info(f"Отправка PUT креатива в ОРД VK v3 на URL: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status in [200, 201]:
                    try:
                        data = await response.json()
                        erid = data.get("erid")
                        if erid:
                            return erid
                    except Exception as json_err:
                        logger.error(f"Ошибка парсинга JSON ОРД: {json_err}")
                    
                    raise Exception(f"ОРД вернул {response.status}, но erid нет в ответе: {resp_text}")
                
                raise Exception(f"Ошибка ОРД VK при создании креатива ({response.status}): {resp_text}")

    async def create_invoice(self, invoice_number, date, date_start, date_end, amount_value, contract_ext_id, client_role="advertiser", contractor_role="agency", items=None):
        """Регистрация/обновление акта методом PUT (v3) + /ready (v2)"""
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        url_put = f"{self.BASE_URL}/v3/invoice/{invoice_ext_id}"
        
        # Точный расчет копеек НДС для прохождения валидаторов ОРД/ЕРИР
        total = float(amount_value)
        excluding_vat = round(total / 1.2, 2)
        vat = round(total - excluding_vat, 2)

        if items is None:
            items = [
                {
                    "contract_external_id": contract_ext_id,
                    "amount": {
                        "including_vat": str(total),
                        "vat_rate": "20",
                        "excluding_vat": str(excluding_vat),
                        "vat": str(vat)
                    }
                }
            ]

        payload = {
            "contract_external_id": contract_ext_id,
            "date": date,
            "serial": str(invoice_number),
            "date_start": date_start,
            "date_end": date_end,
            "amount": {
                "services": {
                    "including_vat": str(total),
                    "vat_rate": "20",
                    "excluding_vat": str(excluding_vat),
                    "vat": str(vat)
                }
            },
            "client_role": client_role,
            "contractor_role": contractor_role,
            "items": items
        }

        async with aiohttp.ClientSession() as session:
            # Шаг 1: Сохранение акта
            async with session.put(url_put, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status not in [200, 201]:
                    raise Exception(f"Ошибка ОРД VK при сохранении акта ({response.status}): {resp_text}")
            
            # Шаг 2: Сигнал готовности для ЕРИР (/ready использует v2)
            url_ready = f"{self.BASE_URL}/v2/invoice/{invoice_ext_id}/ready"
            async with session.post(url_ready, headers=self.headers) as response_ready:
                resp_ready_text = await response_ready.text()
                if response_ready.status in [200, 201]:
                    logger.info(f"Акт {invoice_ext_id} успешно отправлен в ЕРИР.")
                    return invoice_ext_id
                
                raise Exception(f"Акт сохранен, но ошибка на этапе /ready ({response_ready.status}): {resp_ready_text}")
