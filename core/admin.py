from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, 
    BloggerProfile, 
    AdvertiserProfile, 
    ProductAd, 
    Message, 
    SupportTicket, 
    AdIntegration,
    SavedContractor,  
    OrdContract, 
    KktuCode, 
    EridIntegration
)

class CustomUserAdmin(BaseUserAdmin):
    # Теперь список пользователей вернется, и в нем появится колонка Telegram
    list_display = ('username', 'email', 'telegram', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'telegram')
    
    # 3. Добавляем поле telegram внутрь самой карточки пользователя, 
    # чтобы его можно было там увидеть и отредактировать
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('role', 'telegram', 'tg_chat_id')}),
    )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chat', 'created_at', 'is_from_tg', 'is_read') 
    list_filter = ('is_from_tg', 'created_at', 'chat')
    search_fields = ('text', 'sender__email')

# Регистрируем остальные модели
admin.site.register(BloggerProfile)
admin.site.register(AdvertiserProfile)
admin.site.register(ProductAd)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')

@admin.register(AdIntegration)
class AdIntegrationAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'brand', 'channel_name', 'views', 'cost', 'cpv', 'publish_date')
    search_fields = ('product_name', 'brand', 'channel_name')
    list_filter = ('publish_date', 'brand')
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
    list_display = ('creative_name', 'erid', 'invoice_number', 'invoice_amount')
    search_fields = ('creative_name', 'blogger_name', 'channel_url')
    
    fieldsets = (
        ('Данные интеграции', {
            'fields': ('ord_contract', 'kktu', 'blogger_name', 'advertiser_name', 'channel_url', 'creative_name')
        }),
        ('Статус маркировки', {
            'fields': ('erid',),
        }),
        ('Отчетность (акты)', {
            'fields': ('invoice_number', 'invoice_date', 'invoice_amount'),
            'classes': ('collapse',), 
        }),
    )
    
    readonly_fields = ('erid',) 
    actions = ['sync_with_ord']

    @admin.action(description="Синхронизировать с ОРД")
    def sync_with_ord(self, request, queryset):
        pass
