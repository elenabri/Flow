import logging
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Импортируем модуль views один раз — код станет чище
from core import views  

logger = logging.getLogger(__name__)

# =====================================================================
# --- ВНУТРЕННИЕ МАРШРУТЫ ПРИЛОЖЕНИЯ (NAMESPACE: 'core') ---
# =====================================================================
core_patterns = ([
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Маркировка рекламы ОРД VK v3
    path('erid/', views.EridManagementView.as_view(), name='erid_management'),
    path('delete-contractor/<str:external_id>/', views.delete_contractor, name='delete_contractor'),
    
    # Объявления (Маркетплейс "Вкусневич" и др.)
    path('marketplace/', views.marketplace, name='ad_list'), 
    path('my-ads/', views.manage_products, name='my_ads'), 
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('my-products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('my-products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    
    # Блогеры и профили
    path('bloggers/', views.blogger_list, name='blogger_list'),
    path('blogger/<int:blogger_id>/', views.blogger_detail, name='blogger_detail'),
    path('blogger/profile/edit/', views.edit_profile, name='edit_profile'), 
    path('seller/<int:pk>/', views.seller_profile, name='seller_profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    
    # Взаимодействие, отклики и интеграции YouTube
    path('integration/', views.integration_list, name='integration_list'),
    path('integration/add/', views.add_integration, name='add_integration'),
    path('integration/delete/<int:item_id>/', views.delete_integration, name='delete_integration'),
    path('integration/update/<int:item_id>/', views.update_integration_views, name='update_views'),
    path('send_response/<int:ad_id>/', views.send_response, name='send_response'),
    
    # Внутренняя система чатов
    path('chats/', views.chat_list, name='chat_list'),
    path('chat/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('chats/room/<int:chat_id>/', views.chat_room_by_id, name='chat_room_by_id'),

    # Технические API-эндпоинты и AJAX
    path('api/fetch-youtube/', views.fetch_youtube_data, name='fetch_youtube'),
    path('ajax/check-email/', views.check_email, name='check_email'),
    path('support-ajax/', views.support_ajax, name='support_ajax'),
    path('api/connect-telegram/', views.connect_telegram_api, name='connect_telegram_api'),
    path('bulk-message-setup/', views.bulk_message_setup, name='bulk_message_setup'),
    
    # Авторизация и активация (Интегрировано в core)
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('registration-success/', views.registration_success, name='registration_success'),
    path('login-router/', views.login_router, name='login_router'),
], 'core')


# =====================================================================
# --- ГЛОБАЛЬНЫЕ МАРШРУТЫ ПРОЕКТА ---
# =====================================================================
urlpatterns = [
    # Панель администратора
    path('admin/', admin.site.urls),
    
    # Верификация (Вынесена на глобальный уровень, если не требует namespace)
    path('verify-email/<path:username>/', views.verify_email, name='verify_email'),
    
    # Подключение путей основного приложения
    path('', include(core_patterns)),

    # Встроенные контейнеры авторизации Django (login, logout)
    path('accounts/', include('django.contrib.auth.urls')),

    # Ручное переопределение цепочки восстановления пароля (Безопасный перенос)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Telegram Webhook для работы с ботом уведомлений
    path('tg-webhook-8275098246/', views.telegram_webhook, name='telegram_webhook'),
]

# Сборка медиафайлов и статики
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
