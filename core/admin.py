from django.contrib import admin
from .models import (
    User, 
    BloggerProfile, 
    AdvertiserProfile, 
    ProductAd, 
    Message, 
    SupportTicket, 
    AdIntegration,
    SavedContractor,  # <--- Вот этого импорта вам не хватало
    OrdContract, 
    KktuCode, 
    EridIntegration
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'telegram','role', 'is_staff')
    list_filter = ('role',)
    search_fields = ('username','telegram', 'email')

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
@admin.register(SavedContractor)
class SavedContractorAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'contractor_type', 'inn')
    list_filter = ('role', 'contractor_type')
    search_fields = ('name', 'inn')

@admin.register(OrdContract)
class OrdContractAdmin(admin.ModelAdmin):
    list_display = ('number', 'advertiser', 'blogger', 'date_sign')
    search_fields = ('number', 'advertiser__name', 'blogger__name')

@admin.register(KktuCode)
class KktuCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)

@admin.register(EridIntegration)
class EridIntegrationAdmin(admin.ModelAdmin):
    # Добавили video_url в list_display для удобства
    list_display = ('creative_name', 'erid', 'external_id', 'video_url', 'invoice_number', 'invoice_amount')
    
    # Добавили поиск по external_id
    search_fields = ('creative_name', 'blogger_name', 'erid', 'external_id')
    
    fieldsets = (
        ('Данные интеграции', {
            'fields': ('ord_contract', 'kktu', 'blogger_name', 'advertiser_name', 
                       'channel_url', 'creative_name', 'video_url', 'external_id')
        }),
        ('Статус маркировки', {
            'fields': ('erid',),
        }),
        ('Отчетность (акты)', {
            'fields': ('invoice_number', 'invoice_date', 'invoice_amount'),
            'classes': ('collapse',),
        }),
    )
    
    # external_id оставляем редактируемым, так как он присваивается нашей системой
    readonly_fields = ('erid',) 
    
    actions = ['sync_with_ord']

    @admin.action(description="Синхронизировать с ОРД")
    def sync_with_ord(self, request, queryset):
        # Здесь будет логика вызова API
        self.message_user(request, "Синхронизация запущена...")
