import logging
import uuid
import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)

async def send_telegram_message(recipient_tg_id, title, text):
    # Токен и логику отправки оставляем без изменений, но рекомендуется выносить токен в settings.py
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k")
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


class VKORDService:
    """Сервис для интеграции с API ОРД VK по официальной спецификации"""
    
    # Базовый домен песочницы ОРД VK без указания конкретной версии
    BASE_URL = "https://api-sandbox.ord.vk.com" 
    
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def create_person(self, data):
        """Регистрация контрагента через метод PUT по спецификации ОРД VK v1"""
        external_id = data.pop("external_id", None) or f"per_{uuid.uuid4().hex[:10]}"
        
        # Использует версию v1 по спецификации
        url = f"{self.BASE_URL}/v1/person/{external_id}"
        
        logger.info(f"Отправка PUT-запроса контрагента в ОРД VK v1 на URL: {url} с телом: {data}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=self.headers) as response:
                resp_text = await response.text()
                
                if response.status in [200, 201]:
                    logger.info(f"Контрагент успешно сохранен в ОРД. ID: {external_id}")
                    return external_id
                
                raise Exception(
                    f"Ошибка ОРД VK при создании контрагента (Status {response.status}). "
                    f"Отправлено: {data}. Ответ ОРД: {resp_text}"
                )

    async def create_pad(self, blogger_external_id, channel_url, channel_name):
        """Регистрация площадки (YouTube-каналы и т.д.) v1"""
        # Эндпоинт требует версию v1
        url = f"{self.BASE_URL}/v1/pads/"
        payload = {
            "external_id": f"pad_{uuid.uuid4().hex[:10]}",
            "person_external_id": blogger_external_id,
            "type": "media",  
            "url": channel_url,
            "name": channel_name
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status in [200, 201]:
                    return True
                resp_text = await response.text()
                raise Exception(f"Ошибка ОРД VK при регистрации площадки: {resp_text}")

    async def create_contract(self, contract_ext_id, payload):
        """Создание договора оказания услуг методом PUT по спецификации ОРД VK v1"""
        # Договоры регистрируются через v1
        url = f"{self.BASE_URL}/v1/contract/{contract_ext_id}"
        
        logger.info(f"Отправка PUT-запроса договора в ОРД VK v1 на URL: {url} с телом: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                
                if response.status in [200, 201]:
                    logger.info(f"Договор успешно зарегистрирован в ОРД. ID: {contract_ext_id}")
                    return contract_ext_id
                
                raise Exception(
                    f"Ошибка ОРД VK при создании договора (Status {response.status}). "
                    f"Отправлено: {payload}. Ответ ОРД: {resp_text}"
                )

    async def upload_media(self, video_file):
        """Загрузка медиафайла методом PUT по спецификации ОРД VK v1"""
        media_external_id = f"med_{uuid.uuid4().hex[:10]}"
        # Медиафайлы загружаются через префикс v1
        url = f"{self.BASE_URL}/v1/media/{media_external_id}"
        
        logger.info(f"Загрузка медиафайла в ОРД VK v1 на URL: {url}")
        
        data = aiohttp.FormData()
        file_bytes = video_file.read()
        data.add_field('media_file', file_bytes, filename=video_file.name)
        
        # Исключаем Content-Type из заголовков, чтобы aiohttp автоматически выставил multipart/form-data с границей (boundary)
        upload_headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
        
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data, headers=upload_headers) as response:
                resp_text = await response.text()
                
                if response.status in [200, 201]:
                    logger.info(f"Медиафайл успешно загружен в ОРД. ID: {media_external_id}")
                    return media_external_id
                
                raise Exception(
                    f"Ошибка ОРД VK при загрузке видео (Status {response.status}). Ответ ОРД: {resp_text}"
                )

    async def create_creative(self, creative_ext_id, payload):
        """Создание креатива методом PUT по спецификации ОРД VK v3"""
        # Креативы строго требуют v3 эндпоинт
        url = f"{self.BASE_URL}/v3/creative/{creative_ext_id}"
        
        logger.info(f"Отправка PUT-запроса креатива в ОРД VK v3 на URL: {url} с телом: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                
                if response.status in [200, 201]:
                    try:
                        data = await response.json()
                        erid = data.get("erid")
                        if erid:
                            logger.info(f"Креатив успешно создан. Получен ERID: {erid}")
                            return erid
                    except Exception as json_err:
                        logger.error(f"Не удалось распарсить JSON ответа ОРД: {resp_text}. Ошибка: {json_err}")
                    
                    raise Exception(f"ОРД VK вернул статус {response.status}, но ERID отсутствует в ответе: {resp_text}")
                
                raise Exception(
                    f"Ошибка ОРД VK при создании креатива (Status {response.status}). "
                    f"Отправлено: {payload}. Ответ ОРД: {resp_text}"
                )

    async def create_invoice(self, invoice_number, date, date_start, date_end, amount_value, contract_ext_id, client_role="advertiser", contractor_role="agency", items=None):
        """
        Регистрация/обновление акта методом PUT по спецификации ОРД VK v3 
        с последующим подтверждением готовности к отправке в ЕРИР.
        """
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        
        # Шаг 1: Формирование эндпоинта создания полного акта (v3)
        url_put = f"{self.BASE_URL}/v3/invoice/{invoice_ext_id}"
        
        # Если детализация (items) не передана, формируем базовую разаллокацию по изначальному договору
        if items is None:
            items = [
                {
                    "contract_external_id": contract_ext_id,
                    "amount": {
                        "including_vat": str(amount_value),
                        "vat_rate": "20",  # Укажите актуальную ставку НДС (например, 20, 10 или 0)
                        "excluding_vat": str(round(float(amount_value) / 1.2, 2)),
                        "vat": str(round(float(amount_value) - (float(amount_value) / 1.2), 2))
                    }
                }
            ]

        # Собираем структуру payload строго по спецификации v3
        payload = {
            "contract_external_id": contract_ext_id,
            "date": date,              # Формат: "YYYY-MM-DD"
            "serial": str(invoice_number),
            "date_start": date_start,  # Формат: "YYYY-MM-DD"
            "date_end": date_end,      # Формат: "YYYY-MM-DD"
            "amount": {
                "services": {
                    "including_vat": str(amount_value),
                    "vat_rate": "20",
                    "excluding_vat": str(round(float(amount_value) / 1.2, 2)),
                    "vat": str(round(float(amount_value) - (float(amount_value) / 1.2), 2))
                }
            },
            "client_role": client_role,
            "contractor_role": contractor_role,
            "items": items
        }

        async with aiohttp.ClientSession() as session:
            # Отправка PUT запроса для сохранения черновика акта
            logger.info(f"Отправка PUT-запроса акта в ОРД VK v3 на URL: {url_put}")
            async with session.put(url_put, json=payload, headers=self.headers) as response:
                resp_text = await response.text()
                if response.status not in [200, 201]:
                    raise Exception(f"Ошибка ОРД VK при сохранении акта (Status {response.status}): {resp_text}")
            
            # Шаг 2: Сигнал готовности отправки акта в ЕРИР (v2 /ready) — ОБЯЗАТЕЛЬНО для API актов
            url_ready = f"{self.BASE_URL}/v2/invoice/{invoice_ext_id}/ready"
            logger.info(f"Отправка POST-запроса готовности акта в ЕРИР на URL: {url_ready}")
            async with session.post(url_ready, headers=self.headers) as response_ready:
                resp_ready_text = await response_ready.text()
                if response_ready.status in [200, 201]:
                    logger.info(f"Акт {invoice_ext_id} успешно зарегистрирован и отправлен в ЕРИР.")
                    return invoice_ext_id
                
                raise Exception(f"Акт создан, но произошла ошибка при отправке /ready в ЕРИР: {resp_ready_text}")
