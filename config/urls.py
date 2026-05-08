from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views  
from core.views import telegram_webhook

# Группируем все маршруты основного приложения с именем 'core'
core_patterns = ([
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Объявления (Маркетплейс)
    path('marketplace/', views.marketplace, name='ad_list'), # Общий список для всех
    path('my-ads/', views.manage_products, name='my_ads'), # Только свои для рекламодателя
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('my-products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('my-products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    
    # Блогеры
    path('bloggers/', views.marketplace, name='blogger_list'), # Список блогеров (можно натравить на другой view)
    path('blogger/<int:blogger_id>/', views.blogger_detail, name='blogger_detail'),
    path('blogger/profile/edit/', views.edit_blogger_profile, name='edit_profile'), # Настройка цен
    
    # Взаимодействие и Интеграции
    path('integration/', views.integration, name='integration_list'), # Список сделок "Моя реклама"
    path('seller/<int:pk>/', views.seller_profile, name='seller_profile'),
    path('send_response/<int:ad_id>/', views.send_response, name='send_response'),
    
    # Чаты
    path('chats/', views.chat_list, name='chat_list'),
    path('chat/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('chats/room/<int:chat_id>/', views.chat_room_by_id, name='chat_room_by_id'),

    # API и технические пути
    path('api/fetch-youtube/', views.fetch_youtube_data, name='fetch_youtube'),
    path('ajax/check-email/', views.check_email, name='check_email'),
    path('support-ajax/', views.support_ajax, name='support_ajax'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('login-router/', views.login_router, name='login_router'),
    path('api/connect-telegram/', views.connect_telegram_api, name='connect_telegram_api'),
    path('bulk-message-setup/', views.bulk_message_setup, name='bulk_message_setup'),
    path('update-profile/', views.update_profile, name='update_profile'),
    
], 'core')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test-path/', views.home), 
    path('verify-email/<path:username>/', views.verify_email, name='verify_email'),
    
    # Основные пути приложения
    path('', include(core_patterns)),

    # Встроенная авторизация
    path('accounts/', include('django.contrib.auth.urls')),

    # Сброс пароля
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
    
    path('tg-webhook-8275098246/', telegram_webhook),
]

# Медиа и статика
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
