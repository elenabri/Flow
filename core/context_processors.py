from .models import Message

def unread_messages_count(request):
    if request.user.is_authenticated:
        # Считаем сообщения в чатах пользователя, где отправитель не он сам
        count = Message.objects.filter(
            chat__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return {'unread_count': count}
    return {'unread_count': 0}
