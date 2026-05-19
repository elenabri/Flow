import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Message

def send_telegram_notification(chat_id, text):
    """Отправка сообщения в Telegram через Bot API"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки сигнала в TG: {e}")

@receiver(post_save, sender=Message)
def sync_message_to_telegram(sender, instance, created, **kwargs):
    """
    Срабатывает при сохранении сообщения. 
    Если сообщение создано на сайте, отправляем его в Telegram собеседнику.
    """
    if created and not instance.is_from_tg:
        chat = instance.chat
        sender_user = instance.sender
        
        # Находим получателя (тот, кто в чате, но не отправитель)
        recipient = chat.participants.exclude(id=sender_user.id).first()
        
        if recipient and recipient.tg_chat_id:
            # Формируем красивый заголовок темы (бренд или канал)
            topic = chat.title if chat.title else "Новое сообщение"
            
            # Собираем текст: Жирным тему, затем имя отправителя и само сообщение
            message_text = (
                f"<b>📩 {topic}</b>\n"
                f"От: {sender_user.username}\n"
                f"────────────────\n"
                f"{instance.text}\n\n"
                f"<i>Чтобы ответить, пишите прямо здесь.</i>"
            )
            
            send_telegram_notification(recipient.tg_chat_id, message_text)
