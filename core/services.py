import logging
import uuid
import requests
from django.conf import settings
import json

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
        logger.debug(f"Payload отправляемый в TG: {json.dumps(payload)}")
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
            logger.debug(f"Payload контрагента: {json.dumps(data)}")
            response = self.session.put(url, json=data, timeout=15)
            if response.status_code in [200, 201]:
                logger.info(f"Контрагент успешно сохранен в ОРД VK v1. ID: {external_id}")
                return external_id
            raise Exception(f"Ошибка ОРД VK v1 ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании контрагента: {e}")

    def create_contract(self, contract_ext_id, payload):
        """Регистрация договора по спецификации v1 (метод PUT)"""
        url = f"{self.BASE_URL}/v1/contract/{contract_ext_id}"
        try:
            logger.debug(f"Payload договора: {json.dumps(payload)}")
            response = self.session.put(url, json=payload, timeout=15)
            response.raise_for_status()
            return contract_ext_id
        except requests.RequestException as e:
            raise Exception(f"Сетевая ошибка при создании договора: {e}")

    def create_pad(self, pad_ext_id, person_ext_id, name, url):
        final_url = url
        if url.strip('/') == "https://youtube.com":
            final_url = "https://youtube.com/channel/example_detailed_path"
            
        payload = {
            "person_external_id": person_ext_id,
            "is_owner": True,
            "type": "web",
            "name": name,
            "url": final_url 
        }
        logger.debug(f"Payload площадки: {json.dumps(payload)}")
        response = self.session.put(f"{self.BASE_URL}/v1/pad/{pad_ext_id}", json=payload)
        
        if response.status_code != 200:
            logger.error(f"ОТВЕТ ОРД VK (create_pad): {response.text}")
            
        response.raise_for_status()
        return pad_ext_id

    def get_pads(self, person_ext_id=None):
        """Получение списка площадок"""
        url = f"{self.BASE_URL}/v1/pad"
        params = {"person_external_id": person_ext_id} if person_ext_id else {}
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("items", data) if isinstance(data, dict) else data

    def find_or_create_pad(self, person_ext_id, url):
        try:
            existing_pads = self.get_pads(person_ext_id=person_ext_id)
            for pad in existing_pads:
                if pad.get('url', '').strip('/') == url.strip('/'):
                    return pad.get('external_id') or pad.get('id')
        except Exception as e:
            logger.warning(f"Ошибка при поиске площадки: {e}")

        new_pad_ext_id = f"pad_{uuid.uuid4().hex[:10]}"
        self.create_pad(new_pad_ext_id, person_ext_id, "YouTube канал (Авто)", url)
        return new_pad_ext_id

    def upload_media(self, video_file):
        media_external_id = f"med_{uuid.uuid4().hex[:10]}"
        url = f"{self.BASE_URL}/v1/media/{media_external_id}"
        headers = {"Authorization": self.session.headers["Authorization"]}
        
        video_file.seek(0)
        files = {'media_file': (video_file.name, video_file.read(), 'video/mp4')}
        
        response = requests.put(url, files=files, headers=headers, timeout=60)
        response.raise_for_status()
        return media_external_id

    def create_creative(self, creative_ext_id, payload):
        url = f"{self.BASE_URL}/v3/creative/{creative_ext_id}"
        logger.debug(f"Payload креатива: {json.dumps(payload)}")
        response = self.session.put(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json().get("erid")

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
            "contractor_role": "publisher",
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
            logger.debug(f"Payload отправляемый в ОРД: {json.dumps(payload)}")
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
        logger.debug(f"Payload отправляемый в ОРД: {json.dumps(payload)}")
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
