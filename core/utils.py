# core/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

def send_verification_email(user, password, request=None):
    domain = getattr(settings, 'SITE_DOMAIN', '127.0.0.1:8000')
    protocol = 'https' if not settings.DEBUG else 'http'
    
    # Генерируем безопасные параметры
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    
    # Ссылка должна соответствовать функции activate
    activation_link = f"{protocol}://{domain}/activate/{uid}/{token}/"

    context = {
        'user': user,
        'temp_password': password,
        'link': activation_link
    }

    # ВНИМАНИЕ: Проверь этот путь! 
    # Он должен точно совпадать с папками в templates
    try:
        html_content = render_to_string('core/verify_email.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            "Подтверждение регистрации Vkusnevich",
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f"Письмо успешно отправлено на {user.email}")
        
    except Exception as e:
        # Это выведет ошибку в консоль, если что-то пойдет не так
        print(f"Ошибка внутри send_verification_email: {e}")
        raise e # Оставляем raise, чтобы view тоже видела ошибку

from telebot import types
from .models import Chat, Message


def get_main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # ИСПОЛЬЗУЕМ ВАШ РЕАЛЬНЫЙ АДРЕС ИЗ ЛОГОВ RENDER
    # Обязательно со слэшем в конце /chats/
    web_app = types.WebAppInfo(url="https://tubeflow-mvfo.onrender.com/chats/")
    
    btn_webapp = types.KeyboardButton(text="📱 Открыть Мессенджер", web_app=web_app)
    btn_main = types.KeyboardButton(text="🏠 Главная")
    
    markup.row(btn_webapp)
    # Добавляем кнопку профиля или вторую кнопку в ряд
    markup.row(btn_main, types.KeyboardButton(text="📂 Мои диалоги"))
    return markup

# Инлайн-кнопки со списком чатов
def get_chats_inline(user, only_unread=False):
    markup = types.InlineKeyboardMarkup()
    chats = Chat.objects.filter(participants=user)
    
    if only_unread:
        # Показываем только те, где есть непрочитанные (не от нас)
        chats = chats.filter(messages__is_read=False).exclude(messages__sender=user).distinct()

    for chat in chats:
        # Используем ваш метод из модели для красивого имени
        opponent_name = chat.get_opponent_name(user)
        unread_count = chat.messages.filter(is_read=False).exclude(sender=user).count()
        
        icon = "🔴 " if unread_count > 0 else ""
        count_str = f" (+{unread_count})" if unread_count > 0 else ""
        
        markup.add(types.InlineKeyboardButton(
            text=f"{icon}{opponent_name}{count_str}", 
            callback_data=f"select_chat_{chat.id}"
        ))
    return markup
import telebot
from django.conf import settings

def send_telegram_notification(receiver_user, message_text, sender_name, chat_id):
    # Исправлено на tg_chat_id (как в вашей модели User)
    if not receiver_user.tg_chat_id:
        return

    bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)
    
    # Используем HTML, так как Markdown иногда "падает" на спецсимволах
    text = (
        f"📩 <b>Новое сообщение от {sender_name}</b>\n\n"
        f"{message_text}\n\n"
        f"Чтобы ответить, откройте мессенджер в меню."
    )
    
    try:
        bot.send_message(receiver_user.tg_chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# core/utils.py
import re
from googleapiclient.discovery import build

def get_youtube_views(video_url, api_key):
    # Извлекаем ID видео из ссылки с помощью регулярного выражения
    video_id_match = re.search(r"v=([^&]+)", video_url) or re.search(r"be/([^?]+)", video_url)
    if not video_id_match:
        return None
    
    video_id = video_id_match.group(1)
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.videos().list(
        part="statistics",
        id=video_id
    )
    response = request.execute()

    if response['items']:
        return int(response['items'][0]['statistics']['viewCount'])
    return 0
