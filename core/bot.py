import os
import telebot # pip install pyTelegramBotAPI
from django.conf import settings
from .models import User

# Инициализация бота
bot = telebot.TeleBot('ТВОЙ_ТОКЕН_БОТА')

@bot.message_handler(commands=['start'])
def start(message):
    # Команда придет в виде /start 15
    command_text = message.text.split()
    
    if len(command_text) > 1:
        user_id = command_text[1]
        try:
            user = User.objects.get(id=user_id)
            user.tg_chat_id = message.chat.id
            user.save()
            bot.reply_to(message, f"✅ Аккаунт {user.email} успешно привязан! Теперь вы будете получать сообщения здесь.")
        except User.DoesNotExist:
            bot.reply_to(message, "❌ Ошибка: пользователь не найден.")
    else:
        bot.reply_to(message, "Пожалуйста, используйте ссылку из личного кабинета на сайте.")

# Эту функцию будем вызывать из Django, когда кто-то пишет на сайте
def send_sync_message(chat_id, title, text):
    formatted_text = f"<b>{title}</b>\n\n{text}"
    bot.send_message(chat_id, formatted_text, parse_mode='HTML')
