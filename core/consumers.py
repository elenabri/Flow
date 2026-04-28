import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
User = get_user_model() # Это автоматически подтянет твой core.User
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

    
@database_sync_to_async
def save_message(self, text):
    # self.chat_id берется из URL при подключении
    from .models import Message, Chat
    
    # Получаем объект чата
    chat_obj = Chat.objects.get(id=self.chat_id)
    
    # Создаем сообщение, привязанное к чату
    return Message.objects.create(
        chat=chat_obj,
        sender=self.user,
        text=text
    )
