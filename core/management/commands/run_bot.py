import telebot
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import User  # Проверь, что модель называется именно так

# Твой токен
TOKEN = '8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k'

class Command(BaseCommand):
    help = 'Запуск Telegram-бота TubeFlow Support'

    def handle(self, *args, **options):
        bot = telebot.TeleBot(TOKEN)

        @bot.message_handler(commands=['start'])
        def start(message):
            # Разбираем команду /start <user_id>
            parts = message.text.split()
            
            if len(parts) > 1:
                django_user_id = parts[1]
                tg_chat_id = message.chat.id
                
                try:
                    user = User.objects.get(id=django_user_id)
                    user.tg_chat_id = tg_chat_id
                    user.save()
                    
                    bot.send_message(tg_chat_id, f"✨ Привет, {user.username}! Аккаунт привязан.")
                except User.DoesNotExist:
                    bot.send_message(tg_chat_id, "❌ Пользователь не найден.")
        self.stdout.write(self.style.SUCCESS("--- Бот @TubeFlowSupport_bot запущен и слушает... ---"))
        bot.polling(none_stop=True)
