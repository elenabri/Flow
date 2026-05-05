import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Chat

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # В routing.py должно быть: re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user = self.scope['user']
        self.room_group_name = f'chat_{self.chat_id}'

        # Присоединяемся к группе чата
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Покидаем группу чата
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message', '')

        if not message_text:
            return

        # Сохраняем в базу данных (метод теперь внутри класса)
        await self.save_message(message_text)

        # Отправляем сообщение всем участникам группы
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender_id': self.user.id,
                'sender_name': self.user.username
            }
        )

    # Этот метод отвечает за непосредственную отправку данных в WebSocket
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name']
        }))

    # МЕТОД СОХРАНЕНИЯ (Теперь с правильными отступами внутри класса)
    @database_sync_to_async
    def save_message(self, text):
        try:
            # Находим чат по ID, переданному в URL
            chat_obj = Chat.objects.get(id=self.chat_id)
            
            # Создаем сообщение. 
            # Убедись, что в models.py поле связи с чатом называется 'chat'
            return Message.objects.create(
                chat=chat_obj,
                sender=self.user,
                text=text
            )
        except Exception as e:
            print(f"Ошибка при сохранении сообщения: {e}")
            return None
