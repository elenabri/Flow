import logging
import uuid
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def send_telegram_message(recipient_tg_id, title, text):
    """Синхронная отправка уведомлений в Telegram"""
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        logger.error("Отмена отправки TG: Токен TELEGRAM_BOT_TOKEN не обнаружен в settings.py")
        # Как мудрый коллега замечу: не забудьте прописать токен в вашем .env
        return None
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    formatted_text = f"<b>{title}</b>\n\n{text}"
    payload = {
        "chat_id": recipient_tg_id,
        "text": formatted_text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
        return None


class VKORDService:
    """Синхронный сервис для бесшовной интеграции с API ОРД VK по спецификации v3"""
    
    BASE_URL = "https://api-sandbox.ord.vk.com" 
    
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def create_person(self, data):
        """Регистрация контрагента по спецификации v3 (метод PUT)"""
        external_id = data.pop("external_id", None) or f"per_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v3/person/{external_id}"
        
        # В API v3 роли контрагента ("roles") отправляются плоским массивом в корне
        # Убедимся, что juridical_details содержит корректные типы
        logger.info(f"Синхронный PUT контрагента в ОРД VK v3: {url}")

        try:
            response = requests.put(url, json=data, headers=self.headers, timeout=15)
            if response.status in [200, 201]:
                logger.info(f"Контрагент успешно сохранен в ОРД VK v3. ID: {external_id}")
                return external_id
            
            raise Exception(f"Ошибка ОРД VK v3 ({response.status}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании контрагента в ОРД: {e}")

    def create_contract(self, contract_ext_id, payload):
        """Регистрация договора по спецификации v3 (метод PUT)"""
        url = f"{self.BASE_URL}/v3/contract/{contract_ext_id}"
        logger.info(f"Синхронный PUT договора в ОРД VK v3: {url}")

        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=15)
            if response.status in [200, 201]:
                logger.info(f"Договор успешно зарегистрирован в v3. ID: {contract_ext_id}")
                return contract_ext_id
            
            raise Exception(f"Ошибка ОРД VK v3 при создании договора ({response.status}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании договора в ОРД: {e}")

    def upload_media(self, video_file):
        """Загрузка медиафайла (креатива) по спецификации v3"""
        media_external_id = f"med_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v3/media/{media_external_id}"
        logger.info(f"Синхронная загрузка медиафайла в ОРД VK v3: {url}")
        
        # Для загрузки файлов убираем заголовок Content-Type, requests выставит multipart/form-data сам
        upload_headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
        
        try:
            video_file.seek(0)  # Сбрасываем указатель файла в начало перед чтением
            files = {
                'media_file': (video_file.name, video_file.read(), 'video/mp4')
            }
            
            response = requests.put(url, files=files, headers=upload_headers, timeout=60)
            if response.status in [200, 201]:
                logger.info(f"Медиафайл успешно загружен в v3. ID: {media_external_id}")
                return media_external_id
            
            raise Exception(f"Ошибка ОРД VK v3 при загрузке медиа ({response.status}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при отправке видео в ОРД: {e}")

    def create_creative(self, creative_ext_id, payload):
        """Регистрация креатива и получение ERID по спецификации v3"""
        url = f"{self.BASE_URL}/v3/creative/{creative_ext_id}"
        logger.info(f"Синхронный PUT креатива в ОРД VK v3: {url}")

        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=20)
            if response.status in [200, 201]:
                data = response.json()
                erid = data.get("erid")
                if erid:
                    return erid
                raise Exception(f"ОРД вернул статус {response.status}, но поле 'erid' отсутствует: {response.text}")
            
            raise Exception(f"Ошибка ОРД VK v3 при создании креатива ({response.status}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при генерации ERID: {e}")

    def create_invoice(self, contract_ext_id, invoice_number, invoice_date, period_start, period_end, amount, allocated_amount, is_vat=True):
        """
        Регистрация и финализация акта выполненных работ (v3)
        Автоматически рассчитывает математику НДС для ЕРИР.
        """
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        url_put = f"{self.BASE_URL}/v3/invoice/{invoice_ext_id}"
        
        # Точный расчет копеек для налоговых валидаторов ЕРИР (20% НДС)
        total = float(amount)
        allocated = float(allocated_amount)
        
        if is_vat:
            excluding_vat = round(total / 1.2, 2)
            vat = round(total - excluding_vat, 2)
            
            alloc_excluding_vat = round(allocated / 1.2, 2)
            alloc_vat = round(allocated - alloc_excluding_vat, 2)
            vat_rate = "20"
        else:
            excluding_vat = total
            vat = 0.0
            alloc_excluding_vat = allocated
            alloc_vat = 0.0
            vat_rate = "0"

        # Структура payload строго адаптирована под иерархию связей v3
        payload = {
            "contract_external_id": contract_ext_id,
            "date": invoice_date.isoformat() if hasattr(invoice_date, 'isoformat') else str(invoice_date),
            "serial": str(invoice_number),
            "date_start": period_start.isoformat() if hasattr(period_start, 'isoformat') else str(period_start),
            "date_end": period_end.isoformat() if hasattr(period_end, 'isoformat') else str(period_end),
            "amount": {
                "services": {
                    "including_vat": str(total),
                    "vat_rate": vat_rate,
                    "excluding_vat": str(excluding_vat),
                    "vat": str(vat)
                }
            },
            "client_role": "advertiser",
            "contractor_role": "publisher",  # В связке Рекламодатель -> Блогер, блогер выступает как Исполнитель (publisher)
            "items": [
                {
                    "contract_external_id": contract_ext_id,
                    "amount": {
                        "including_vat": str(allocated),
                        "vat_rate": vat_rate,
                        "excluding_vat": str(alloc_excluding_vat),
                        "vat": str(alloc_vat)
                    }
                }
            ]
        }

        try:
            # Шаг 1: Регистрация параметров акта в ОРД VK
            response = requests.put(url_put, json=payload, headers=self.headers, timeout=20)
            if response.status not in [200, 201]:
                raise Exception(f"Ошибка ОРД VK v3 при сохранении акта ({response.status}): {response.text}")
            
            # Шаг 2: Сигнал завершения редактирования акта (/ready использует сквозной v2 эндпоинт)
            url_ready = f"{self.BASE_URL}/v2/invoice/{invoice_ext_id}/ready"
            response_ready = requests.post(url_ready, headers=self.headers, timeout=15)
            
            if response_ready.status in [200, 201]:
                logger.info(f"Акт {invoice_ext_id} успешно провалидирован и отправлен в ЕРИР.")
                return invoice_ext_id
                
            raise Exception(f"Акт сохранен, но /ready отклонен ({response_ready.status}): {response_ready.text}")
            
        except requests.RequestException as e:
            raise Exception(f"Сетевой сбой при отправке бухгалтерской отчетности в ОРД: {e}")
