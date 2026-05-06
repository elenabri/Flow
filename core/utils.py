# core/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_verification_email(user, password):
    domain = getattr(settings, 'SITE_DOMAIN', '127.0.0.1:8000')
    protocol = 'https' if not settings.DEBUG else 'http'
    activation_link = f"{protocol}://{domain}/verify-email/{user.username}/"

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

# Главное меню, которое "приклеится" внизу
def get_main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🏠 Главная"), types.KeyboardButton("📂 Мои диалоги"))
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
