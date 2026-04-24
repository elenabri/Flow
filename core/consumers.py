import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope['user']
        
        # Создаем уникальное имя комнаты для двоих пользователей
        # Чтобы и 1-2, и 2-1 попадали в одну комнату
        ids = sorted([int(self.user.id), int(self.other_user_id)])
        self.room_group_name = f'chat_{ids[0]}_{ids[1]}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data['message']

        # Сохраняем в базу данных
        await self.save_message(message_text)

        # Отправляем сообщение всем в комнате
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender_id': self.user.id,
                'sender_name': self.user.username
            }
        )

    async def chat_message(self, event):
        # Отправка в браузер
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name']
        }))

    @database_sync_to_async
    def save_message(self, text):
        other_user = User.objects.get(id=self.other_user_id)
        return Message.objects.create(sender=self.user, receiver=other_user, text=text)
