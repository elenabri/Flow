import aiohttp # Используем асинхронную библиотеку, чтобы сайт не зависал
from django.conf import settings

async def send_telegram_message(recipient_tg_id, title, text):
    token = "ТВОЙ_ТОКЕН_БОТА" # Рекомендую вынести в .env -> settings.TG_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Тот самый "чистый" формат: Тема жирным, ниже текст
    formatted_text = f"<b>{title}</b>\n\n{text}"
    
    payload = {
        "chat_id": recipient_tg_id,
        "text": formatted_text,
        "parse_mode": "HTML"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()
