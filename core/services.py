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
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

    def create_person(self, data):
        """Регистрация контрагента по спецификации v1 (метод PUT)"""
        external_id = data.pop("external_id", None) or f"per_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/person/{external_id}"
        logger.info(f"Синхронный PUT контрагента в ОРД VK v1: {url}")

        try:
            response = self.session.put(url, json=data, timeout=15)
            if response.status_code in [200, 201]:
                logger.info(f"Контрагент успешно сохранен в ОРД VK v1. ID: {external_id}")
                return external_id
            raise Exception(f"Ошибка ОРД VK v1 ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании контрагента в ОРД: {e}")

    def create_contract(self, contract_ext_id, payload):
        """Регистрация договора по спецификации v1 (метод PUT)"""
        url = f"{self.BASE_URL}/v1/contract/{contract_ext_id}"
        logger.info(f"Синхронный PUT договора в ОРД VK v1: {url}")

        try:
            response = self.session.put(url, json=payload, timeout=15)
            if response.status_code in [200, 201]:
                logger.info(f"Договор успешно зарегистрирован в v1. ID: {contract_ext_id}")
                return contract_ext_id
            raise Exception(f"Ошибка ОРД VK v1 при создании договора ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании договора в ОРД: {e}")

    def create_pad(self, pad_ext_id, person_ext_id, name, url):
        """Регистрация площадки"""
        payload = {
            "person_external_id": person_ext_id,
            "is_owner": True,
            "type": "web",
            "name": name,
            "url": url
        }
        response = self.session.put(f"{self.BASE_URL}/v1/pad/{pad_ext_id}", json=payload)
        response.raise_for_status()
        return pad_ext_id

    def upload_media(self, video_file):
        """Загрузка медиафайла (креатива) по спецификации v1"""
        media_external_id = f"med_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/media/{media_external_id}"
        logger.info(f"Синхронная загрузка медиафайла в ОРД VK v1: {url}")
        
        # СОЗДАЕМ КОПИЮ заголовков БЕЗ Content-Type
        headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
        
        try:
            video_file.seek(0)
            files = {
                'media_file': (video_file.name, video_file.read(), 'video/mp4')
            }
            # Передаем headers без Content-Type
            response = self.session.put(url, files=files, headers=headers, timeout=60)
            
            if response.status_code in [200, 201]:
                logger.info(f"Медиафайл успешно загружен в v1. ID: {media_external_id}")
                return media_external_id
            raise Exception(f"Ошибка ОРД VK v1 при загрузке медиа ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при отправке видео в ОРД: {e}")

    def create_creative(self, creative_ext_id, payload):
        """Регистрация креатива и получение ERID по спецификации v3"""
        url = f"{self.BASE_URL}/v3/creative/{creative_ext_id}"
        logger.info(f"Синхронный PUT креатива в ОРД VK v3: {url}")

        try:
            response = self.session.put(url, json=payload, timeout=20)
            if response.status_code in [200, 201]:
                data = response.json()
                erid = data.get("erid")
                if erid:
                    return erid
                raise Exception(f"ОРД вернул статус {response.status_code}, но поле 'erid' отсутствует: {response.text}")
            raise Exception(f"Ошибка ОРД VK v3 при создании креатива ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при генерации ERID: {e}")

    def create_invoice(self, contract_ext_id, invoice_number, invoice_date, period_start, period_end, amount, allocated_amount, is_vat=True):
        invoice_ext_id = f"inv_{uuid.uuid4().hex[:10]}"
        
        total = float(amount)
        vat_rate = 20 if is_vat else 0
        excluding_vat = round(total / 1.20, 2) if is_vat else total
        vat = round(total - excluding_vat, 2) if is_vat else 0.0

        url_put = f"{self.BASE_URL}/v4/invoice/{invoice_ext_id}"
        
        payload = {
            "contract_external_id": contract_ext_id,
            "client_role": "advertiser",
            "contractor_role": "agency",
            "date": invoice_date.isoformat(),
            "serial": str(invoice_number),
            "date_start": period_start.isoformat(),
            "date_end": period_end.isoformat(),
            "amount": {
                "services": {
                    "including_vat": f"{total:.2f}",
                    "vat_rate": str(vat_rate),
                    "excluding_vat": f"{excluding_vat:.2f}",
                    "vat": f"{vat:.2f}"
                }
            },
            "items": [
                {
                    "contract_external_id": contract_ext_id,
                    "name": "Рекламные услуги",
                    "amount": {
                        "including_vat": f"{total:.2f}",
                        "vat_rate": str(vat_rate),
                        "excluding_vat": f"{excluding_vat:.2f}",
                        "vat": f"{vat:.2f}"
                    }
                }
            ]
        }

        try:
            response = self.session.put(url_put, json=payload, timeout=20)
            if response.status_code not in [200, 201]:
                raise Exception(f"Ошибка v4 при создании акта: {response.text}")
            
            url_ready = f"{self.BASE_URL}/v4/invoice/{invoice_ext_id}/ready"
            response_ready = self.session.post(url_ready, timeout=15)
            
            if response_ready.status_code in [200, 201]:
                logger.info(f"Акт {invoice_ext_id} успешно отправлен в ЕРИР (v4).")
                return invoice_ext_id
            raise Exception(f"Акт создан, но /v4/ready отклонил запрос: {response_ready.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка: {e}")
            
    def get_kktu_catalog(self, limit=100, offset=0, search=None):
        url = f"{self.BASE_URL}/v1/dict/kktu"
        params = {"limit": limit, "offset": offset, "search": search}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
