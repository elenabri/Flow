from django.contrib import admin
from .models import User, BloggerProfile, AdvertiserProfile, ProductAd, Message

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role',)
    search_fields = ('username', 'email')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chat', 'created_at', 'is_from_tg', 'is_read') 
    list_filter = ('is_from_tg', 'created_at', 'chat')
    search_fields = ('text', 'sender__email')

# Регистрируем остальные модели
admin.site.register(BloggerProfile)
admin.site.register(AdvertiserProfile)
admin.site.register(ProductAd)


from django.contrib import admin
from .models import SupportTicket

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')

from django.contrib import admin
from .models import AdIntegration  # Импортируйте вашу модель

@admin.register(AdIntegration)
class AdIntegrationAdmin(admin.ModelAdmin):
    # Поля, которые будут отображаться в списке
    list_display = ('product_name', 'brand', 'channel_name', 'views', 'cost', 'cpv', 'publish_date')
    
    # Поля, по которым можно искать
    search_fields = ('product_name', 'brand', 'channel_name')
    
    # Фильтры справа
    list_filter = ('publish_date', 'brand')
    
    # Поле только для чтения (так как оно вычисляемое)
    readonly_fields = ('cpv',)
