import random
import re
import requests
import statistics
import json
import string
import random, string, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, FloatField, Case, When, Value
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# И ваш импорт моделей:
from .models import User, Chat, Message

# Твои локальные файлы
from .forms import RegistrationForm, EmailLoginForm
from .models import (
    BloggerProfile, AdvertiserProfile, ProductAd, 
    Message, AdContract, SupportTicket
)
from .constants import TOPIC_CHOICES, SUB_TOPICS_MAP
from django.shortcuts import render, get_object_or_404, redirect  # Добавлен redirect
from django.contrib.auth.decorators import login_required
from .utils import get_main_menu_keyboard, get_chats_inline # Проверьте имя здесь!


User = get_user_model()
YOUTUBE_API_KEY = 'AIzaSyBIQSgM6nAcLnt5En1E59Ee65jL-NHTJDs'

# --- 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def parse_duration_to_seconds(duration):
    match = re.search(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match: return 0
    d, h, m, s = [int(x) if x else 0 for x in match.groups()]
    return d * 86400 + h * 3600 + m * 60 + s

import statistics  # ОБЯЗАТЕЛЬНО добавьте этот импорт в начало файла

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ СТАТИСТИКИ ---
def get_youtube_stats(channel_url, api_key):
    if not channel_url or not isinstance(channel_url, str):
        return None
    
    handle_match = re.search(r'@([\w\.-]+)', channel_url)
    if not handle_match: 
        return None
    
    handle = handle_match.group(1)
    
    try:
        # 1. Запрос данных канала
        ch_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails,brandingSettings&forHandle={handle}&key={api_key}"
        ch_data = requests.get(ch_url, timeout=7).json()
        
        if not ch_data.get("items"): 
            return None
            
        item = ch_data["items"][0]
        uploads_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # 2. Запрос последних видео для расчета медианы
        v_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_id}&maxResults=50&key={api_key}"
        v_data = requests.get(v_url).json()
        v_ids = [v["contentDetails"]["videoId"] for v in v_data.get("items", [])]
        
        long_views, shorts_views = [], []
        if v_ids:
            stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,statistics&id={','.join(v_ids)}&key={api_key}"
            for v in requests.get(stats_url).json().get("items", []):
                views = int(v["statistics"].get("viewCount", 0))
                # Используем вашу функцию парсинга длительности
                if parse_duration_to_seconds(v["contentDetails"]["duration"]) <= 200:
                    shorts_views.append(views)
                else:
                    long_views.append(views)

        # РЕЗУЛЬТАТ: Совмещаем ключи для моделей (BloggerProfile) и для JS
        return {
            # Для сохранения в БД (модели)
            'channel_name': item["snippet"]["title"],
            'subscribers_count': int(item["statistics"].get("subscriberCount", 0)),
            'avatar_url': item["snippet"]["thumbnails"]["high"]["url"],
            'banner_url': item.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl"),
            'median_views': int(statistics.median(long_views)) if long_views else 0,
            'median_views_shorts': int(statistics.median(shorts_views)) if shorts_views else 0,
            
            # --- ВОТ ЭТИ КЛЮЧИ НУЖНЫ ДЛЯ ВАШЕГО JS В register.html ---
            'status': 'success', # Чтобы сработало условие if (data.status === 'success')
            'title': item["snippet"]["title"], # Вы искали data.title
            'subs': int(item["statistics"].get("subscriberCount", 0)), # Вы искали data.subs
            
            # Остальные вспомогательные ключи
            'name': item["snippet"]["title"],
            'long_median': int(statistics.median(long_views)) if long_views else 0,
            'shorts_median': int(statistics.median(shorts_views)) if shorts_views else 0,
            'api_avatar': item["snippet"]["thumbnails"]["high"]["url"],
            'api_banner': item.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl"),
        }
    except Exception as e:
        print(f"Ошибка API: {e}")
        return None

# --- ИСПРАВЛЕННЫЙ REDIRECT В РЕДАКТИРОВАНИИ ---
@login_required
def edit_blogger_profile(request):
    profile = get_object_or_404(BloggerProfile, user=request.user)
    
    if request.method == 'POST':
        profile.price_start = request.POST.get('price_start', profile.price_start)
        profile.categories = ", ".join(request.POST.getlist('topics'))
        profile.save()
        messages.success(request, "Профиль успешно обновлен!")
        return redirect('core:dashboard') # Добавлен namespace 'core:'
        
    # Убедитесь, что путь к шаблону верный (без лишнего core/core/)
    return render(request, 'core/edit_profile.html', {
        'profile': profile,
        'TOPIC_CHOICES': TOPIC_CHOICES
    })



# --- 2. АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ---
import random
import string
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegistrationForm
from .models import User, BloggerProfile, AdvertiserProfile, ProductAd
from .constants import TOPIC_CHOICES, SUB_TOPICS_MAP # Убедись, что импорты верны
from .utils import send_verification_email # Твоя функция отправки почты

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES) # Добавьте FILES для фото товара
        if form.is_valid():
            try:
                with transaction.atomic(): # Если что-то упадет, откатит всё
                    user = form.save(commit=False)
                    email = form.cleaned_data.get('email')
                    user.email = email
                    user.username = email  
                    
                    pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(pwd)
                    user.is_active = False 
                    user.save()

                    role = form.cleaned_data.get('role')
                    user.role = role # Убедитесь, что роль сохраняется в User
                    user.save()
                    
                    if role == 'blogger':
                        BloggerProfile.objects.create(
                            user=user,
                            channel_name=request.POST.get('api_channel_name') or "YouTube Channel",
                            channel_link=request.POST.get('channel_link'),
                            subscribers_count=int(request.POST.get('api_subs') or 0),
                            median_views=int(request.POST.get('api_long_median') or 0),
                            median_views_shorts=int(request.POST.get('api_shorts_median') or 0),
                            categories=", ".join(request.POST.getlist('topics')),
                            price_start=request.POST.get('price_start') or 0,
                            avatar_url=request.POST.get('api_avatar'),
                            banner_url=request.POST.get('api_banner'),
                        )
                    
                    elif role == 'advertiser':
                        adv = AdvertiserProfile.objects.create(
                            user=user, 
                            company_name=request.POST.get('company_name') or "Новый бренд"
                        )
                        
                        product_title = request.POST.get('title')
                        if product_title:
                            ProductAd.objects.create(
                                advertiser=adv, 
                                name=product_title,
                                description=request.POST.get('description', ''),
                                category=", ".join(request.POST.getlist('topics')),
                                image=request.FILES.get('product_image'),
                                link_wb=request.POST.get('link_wb'),
                                link_ozon=request.POST.get('link_ozon'),
                                is_active=True
                            )

                    # Письмо отправляем ПОСЛЕ сохранения всего в базе
                    send_verification_email(user, pwd)
                    
                    return render(request, 'core/success.html', {
                        'email': user.email, 
                        'password': pwd
                    })

            except Exception as e:
                messages.error(request, f"Ошибка при регистрации: {e}")
                return redirect('core:register')
    else:
        form = RegistrationForm()
        
    return render(request, 'core/register.html', {
        'form': form, 
        'TOPIC_CHOICES': TOPIC_CHOICES
    })

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        # Автоматический вход в систему
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
        # СРАЗУ перенаправляем на маркетплейс
        return redirect('core:dashboard') 
    
    # Если токен невалидный, оставляем страницу с ошибкой
    return render(request, 'core/activation_invalid.html')

def user_login(request):
    if request.method == 'POST':
        # Используйте встроенную форму AuthenticationForm или вашу EmailLoginForm
        # ВАЖНО: передаем request в authenticate
        email = request.POST.get('username') # или из cleaned_data
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('core:dashboard')
            else:
                messages.error(request, "Аккаунт еще не активирован. Проверьте почту.")
        else:
            messages.error(request, "Неверный email или пароль.")
            
    return render(request, 'registration/login.html')


from django.db.models import Count

@login_required
def chat_detail(request, user_id):
    # 1. Получаем пользователя, которому пишем
    other_user = get_object_or_404(User, id=user_id)
    
    # Чтобы не начать чат с самим собой
    if other_user == request.user:
        return redirect('core:chat_list')

    # 2. Ищем существующий чат между текущим юзером и other_user
    # Мы ищем чат, где количество участников = 2 и оба этих юзера там присутствуют
    chat = Chat.objects.annotate(part_count=Count('participants')).filter(
        part_count=2,
        participants=request.user
    ).filter(
        participants=other_user
    ).first()

    # 3. Если такого чата еще нет (первый контакт) — создаем его
    if not chat:
        chat = Chat.objects.create()
        chat.participants.add(request.user, other_user)

    # 4. Обработка отправки нового сообщения через форму (POST)
    if request.method == 'POST':
        txt = request.POST.get('text')
        if txt:
            Message.objects.create(
                sender=request.user,
                chat=chat,
                text=txt
            )
            if other_user.tg_chat_id:
                title = f"✉️ Новое сообщение от {request.user.username}"
                send_sync_message(
                    chat_id=other_user.tg_chat_id, 
                    title=title, 
                    text=txt
                )
            # Если это обычный POST (не AJAX), можно редиректить на тот же URL
            return redirect('core:chat_detail', user_id=user_id)
    

    # 5. Сообщения для отображения
    msgs = chat.messages.all().order_by('created_at')

    return render(request, 'core/chat_detail.html', {
        'chat': chat,
        'other_user': other_user,
        'chat_messages': msgs,
    })

# --- 4. ЧАТ И РАССЫЛКА ---

from core.models import Chat, Message


@login_required
def chat_list(request):
    user_chats = Chat.objects.filter(participants=request.user).order_by('-created_at')
    
    chats_data = {}
    for chat in user_chats:
        # Находим, кто наш собеседник
        opponent = chat.participants.exclude(id=request.user.id).first()
        if opponent:
            # Берем последнее сообщение в этом чате
            last_msg = chat.messages.order_by('-created_at').first()
            chats_data[opponent] = last_msg

    return render(request, 'core/chat_list.html', {
        'chats': chats_data,  # Теперь это словарь, и .items в шаблоне заработает!
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Chat, Message

@login_required
def bulk_message_setup(request):
    if request.method == 'POST':
        txt = request.POST.get('message')
        cat = request.POST.get('category_filter')
        
        bloggers = BloggerProfile.objects.all()
        if cat and cat != 'all':
            bloggers = bloggers.filter(categories__icontains=cat)
            
        for b in bloggers:
            if b.user != request.user:
                # 1. Находим или создаем чат для рассылки
                chat, created = Chat.objects.get_or_create(
                    title=f"Рассылка: {request.user.username}",
                )
                chat.participants.add(request.user, b.user)
                
                # 2. Создаем сообщение
                Message.objects.create(
                    chat=chat, 
                    sender=request.user, 
                    text=f"[РАССЫЛКА] {txt}"
                )
        messages.success(request, "Рассылка завершена!")
        return redirect('core:chat_list')
    return render(request, 'core/bulk_message_setup.html', {'TOPIC_CHOICES': TOPIC_CHOICES})

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import ProductAd, Message


@login_required
def send_response(request, ad_id):
    ad = get_object_or_404(ProductAd, id=ad_id)
    advertiser_user = ad.advertiser.user
    
    if advertiser_user == request.user:
        messages.warning(request, "Вы не можете откликнуться на собственное объявление.")
        return redirect('core:marketplace')

    # Ищем чат именно по этому товару между этими двумя людьми
    chat = Chat.objects.filter(ad=ad, participants=request.user).filter(participants=advertiser_user).first()
    
    if not chat:
        chat = Chat.objects.create(ad=ad, title=f"Товар: {ad.name}")
        chat.participants.add(request.user, advertiser_user)

    Message.objects.create(
        chat=chat,
        sender=request.user,
        text=f"Здравствуйте! Меня заинтересовал ваш товар «{ad.name}». Давайте обсудим интеграцию."
    )
    
    messages.success(request, "Отклик успешно отправлен!")
    return redirect('core:chat_list')

# --- 5. УПРАВЛЕНИЕ И ПРОФИЛЬ ---

@login_required
def manage_products(request):
    adv = get_object_or_404(AdvertiserProfile, user=request.user)
    if request.method == 'POST':
        ProductAd.objects.create(advertiser=adv, name=request.POST.get('title'), category=request.POST.get('category'), image=request.FILES.get('product_image'))
    return render(request, 'core/manage_products.html', {'ads': ProductAd.objects.filter(advertiser=adv)})

@login_required
def delete_product(request, pk):
    get_object_or_404(ProductAd, pk=pk, advertiser__user=request.user).delete()
    return redirect('manage_products')

@login_required
def integration(request):
    contracts = AdContract.objects.filter(Q(advertiser=request.user) | Q(blogger=request.user))
    return render(request, 'core/integrations_list.html', {'contracts': contracts})

@login_required
def approve_final_payment(request, contract_id):
    c = get_object_or_404(AdContract, id=contract_id, advertiser=request.user)
    c.status = 'completed'
    c.save()
    return redirect('integration')

# --- 6. ТЕХНИЧЕСКИЕ (AJAX) ---

# --- 6. ТЕХНИЧЕСКИЕ (AJAX) ---

def fetch_youtube_data(request):
    # 1. Получаем URL или handle из запроса
    channel_url = request.GET.get('handle') or request.GET.get('url')
    
    if not channel_url:
        return JsonResponse({'status': 'error', 'message': 'URL не указан'}, status=200)

    # 2. Вызываем функцию получения статистики
    stats = get_youtube_stats(channel_url, YOUTUBE_API_KEY)
    
    # 3. Проверяем результат и возвращаем ответ с ПРАВИЛЬНЫМИ отступами
    if stats:
        # Отступ 4 пробела от 'if'
        return JsonResponse(stats, safe=False)
    else:
        # 'else' стоит на одном уровне с 'if'
        # Отступ 4 пробела от 'else'
        return JsonResponse({
            'status': 'error', 
            'message': 'Канал не найден или ошибка API'
        }, status=200)

@csrf_exempt
def support_ajax(request):
    if request.method == "POST":
        SupportTicket.objects.create(email=request.POST.get('email'), message=request.POST.get('message'))
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

def home(request): return render(request, 'core/index.html')


# --- 7. ПАНЕЛИ УПРАВЛЕНИЯ (DASHBOARDS) ---


import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ProductAd, Message, AdContract

import json
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import AdContract, Message, ProductAd

@login_required
def dashboard(request):
    user = request.user
    
    # 1. ОБРАБОТКА POST-ЗАПРОСОВ (СОХРАНЕНИЕ)
    if request.method == 'POST':
        # --- ЛОГИКА БЛОГЕРА ---
        if hasattr(user, 'blogger_profile'):
            profile = user.blogger_profile
            try:
                # Цены (защита от пустых строк и букв)
                profile.price_start = request.POST.get('price_start') or 0
                profile.price_middle = request.POST.get('price_middle') or 0
                profile.price_end = request.POST.get('price_end') or 0
                profile.price_shorts = request.POST.get('price_shorts') or 0
                
                # Статистика (обязательно приведение к int)
                profile.median_views = int(request.POST.get('median_views') or 0)
                profile.median_views_shorts = int(request.POST.get('median_views_shorts') or 0)
                
                # Реквизиты
                profile.bank_receiver = request.POST.get('bank_receiver')
                profile.inn = request.POST.get('inn')
                profile.bik = request.POST.get('bik')
                profile.account_number = request.POST.get('account_number')
                
                # Динамические поля
                custom_json = request.POST.get('custom_data_json')
                if custom_json:
                    profile.custom_data = json.loads(custom_json)
                
                profile.save()
                messages.success(request, "Профиль блогера успешно обновлен!")
            except ValueError:
                messages.error(request, "Ошибка: в полях цен или просмотров должны быть только числа.")
            except Exception as e:
                messages.error(request, f"Ошибка при сохранении: {e}")

        # --- ЛОГИКА РЕКЛАМОДАТЕЛЯ ---
        elif hasattr(user, 'advertiser_profile'):
            profile = user.advertiser_profile
            
            # А. Обновление реквизитов компании
            if 'update_company' in request.POST:
                profile.company_name = request.POST.get('company_name', profile.company_name)
                profile.inn = request.POST.get('inn')
                profile.bik = request.POST.get('bik')
                profile.account_number = request.POST.get('account_number')
                profile.ogrn = request.POST.get('ogrn')
                profile.legal_address = request.POST.get('legal_address')
                profile.save()
                messages.success(request, "Данные компании сохранены")

            # Б. Создание нового товара
            elif 'add_product' in request.POST:
                ProductAd.objects.create(
                    advertiser=profile,
                    name=request.POST.get('name'), 
                    short_description=request.POST.get('short_description', '')[:30],
                    description=request.POST.get('description'),
                    additional_info=request.POST.get('additional_info'),
                    barter_terms=request.POST.get('barter_terms'),
                    category=request.POST.get('category'),
                    image=request.FILES.get('product_image'),
                    avatar_url=request.POST.get('avatar_url'),
                    link_wb=request.POST.get('link_wb'),
                    link_ozon=request.POST.get('link_ozon'),
                    link_other=request.POST.get('link_other') 
                )
                messages.success(request, "Товар успешно добавлен в маркетплейс")
        
        # После POST всегда делаем редирект, чтобы избежать повторной отправки формы при обновлении страницы
        return redirect('core:dashboard')

    # 2. ПОДГОТОВКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ (GET)
    context = {'user': user}
    
    if hasattr(user, 'blogger_profile'):
        context['profile'] = user.blogger_profile
        # Используем select_related для оптимизации запросов к БД
        context['active_contracts'] = AdContract.objects.filter(blogger=user)\
            .exclude(status='completed').select_related('advertiser')
        
        # Последние 5 входящих сообщений
        context['recent_messages'] = Message.objects.filter(chat__participants=user)\
            .exclude(sender=user).select_related('sender').order_by('-created_at')[:5]
        
    elif hasattr(user, 'advertiser_profile'):
        context['profile'] = user.advertiser_profile
        # Список товаров рекламодателя
        context['products'] = ProductAd.objects.filter(advertiser=user.advertiser_profile).order_by('-created_at')
        # Контракты
        context['active_contracts'] = AdContract.objects.filter(advertiser=user)\
            .exclude(status='completed').select_related('blogger')

    return render(request, 'core/dashboard.html', context)
    
    
    


# --- 8. AJAX ПРОВЕРКИ ---

def check_email(request):
    """Проверка существования email (для регистрации)"""
    email = request.GET.get('email', None)
    data = {
        'is_taken': User.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)

def check_channel(request):
    """Проверка существования канала (для регистрации блогера)"""
    channel_link = request.GET.get('link', None)
    data = {
        'is_taken': BloggerProfile.objects.filter(channel_link=channel_link).exists()
    }
    return JsonResponse(data)


# --- 9. УПРАВЛЕНИЕ ПРОФИЛЕМ ---

@login_required
def edit_blogger_profile(request):
    """Редактирование данных блогера (цена, категории, описание)"""
    profile = get_object_or_404(BloggerProfile, user=request.user)
    
    if request.method == 'POST':
        profile.price_start = request.POST.get('price_start', profile.price_start)
        profile.categories = ", ".join(request.POST.getlist('topics'))
        # Если есть поле описания в модели:
        # profile.description = request.POST.get('description', profile.description)
        profile.save()
        messages.success(request, "Профиль успешно обновлен!")
        return redirect('dashboard')
        
    return render(request, 'core/edit_profile.html', {
        'profile': profile,
        'TOPIC_CHOICES': TOPIC_CHOICES
    })

@login_required
def edit_advertiser_profile(request):
    """Редактирование данных рекламодателя (название компании)"""
    profile = get_object_or_404(AdvertiserProfile, user=request.user)
    
    if request.method == 'POST':
        profile.company_name = request.POST.get('company_name', profile.company_name)
        profile.save()
        messages.success(request, "Данные компании обновлены!")
        return redirect('dashboard')
        
    return render(request, 'core/edit_advertiser_profile.html', {'profile': profile})


# --- 10. ПУБЛИЧНЫЕ ПРОФИЛИ ---

def seller_profile(request, pk):
    """
    Публичная страница рекламодателя (продавца).
    Показывает информацию о компании и список их активных рекламных кампаний.
    """
    # Ищем профиль рекламодателя по его первичному ключу (ID)
    advertiser = get_object_or_404(AdvertiserProfile, pk=pk)
    
    # Получаем все активные товары/предложения этого рекламодателя
    active_ads = ProductAd.objects.filter(advertiser=advertiser).order_by('-id')
    
    return render(request, 'core/seller_profile.html', {
        'seller': advertiser,
        'ads': active_ads
    })

# --- 11. РОУТИНГ ПОСЛЕ ВХОДА ---

@login_required
def login_router(request):
    """
    Умный редирект: направляет пользователя в нужный дашборд 
    в зависимости от его роли сразу после авторизации.
    """
    user = request.user
    
    if hasattr(user, 'blogger_profile'):
        # Если зашел блогер — ведем в его панель управления
        return redirect('core:dashboard')
        
    elif hasattr(user, 'advertiser_profile'):
        # Если зашел рекламодатель — ведем в его панель
        return redirect('core:dashboard')
    
    # Если профиль по какой-то причине не найден, 
    # отправляем на главную маркетплейса
    return redirect('core:marketplace')



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ProductAd

@login_required
def edit_product(request, pk):
    # Достаем товар или выдаем 404. 
    # Фильтр advertiser__user=request.user гарантирует, что редактировать может только владелец.
    product = get_object_or_404(ProductAd, pk=pk, advertiser__user=request.user)
    
    if request.method == 'POST':
        # 1. Основная информация
        product.name = request.POST.get('name')
        product.category = request.POST.get('category')
        product.description = request.POST.get('description')
        
        # 2. Ссылки на маркетплейсы
        product.link_wb = request.POST.get('link_wb')
        product.link_ozon = request.POST.get('link_ozon')
        product.link_other = request.POST.get('link_other')
        
        # 3. Работа с изображениями
        # Если загружен новый файл — обновляем его
        if request.FILES.get('product_image'):
            product.image = request.FILES.get('product_image')
        
        # Обновляем текстовую ссылку на фото (если есть)
        product.avatar_url = request.POST.get('avatar_url')
        
        # Сохраняем изменения в базе
        product.save()
        
        # Добавляем уведомление для пользователя
        messages.success(request, f"Товар «{product.name}» успешно обновлен!")
        
        # Возвращаемся в личный кабинет
        return redirect('core:dashboard')

    # Если метод GET — просто показываем форму с данными товара
    return render(request, 'core/edit_product.html', {'product': product})



from decimal import Decimal  # Добавьте этот импорт в начало файла

def blogger_detail(request, blogger_id):
    blogger = get_object_or_404(BloggerProfile, id=blogger_id)
    
    # Цены
    p_shorts = blogger.price_start
    p_mid = round(blogger.price_start * Decimal('2.5'), 0)
    p_pre = round(blogger.price_start * Decimal('1.8'), 0)
    p_end = round(blogger.price_start * Decimal('1.2'), 0)

    # Расчеты CPV (Цена / Просмотры)
    cpv_long = 0
    cpv_pre = 0
    if blogger.median_views > 0:
        views_dec = Decimal(str(blogger.median_views))
        cpv_long = round(p_mid / views_dec, 2)
        cpv_pre = round(p_pre / views_dec, 2) # Добавляем это

    cpv_shorts = 0
    if blogger.median_views_shorts > 0:
        cpv_shorts = round(p_shorts / Decimal(str(blogger.median_views_shorts)), 2)

    context = {
        'blogger': blogger,
        'p_shorts': p_shorts,
        'p_mid': p_mid,
        'p_pre': p_pre,
        'p_end': p_end,
        'cpv_long': cpv_long,
        'cpv_pre': cpv_pre,      # Передаем в шаблон
        'cpv_shorts': cpv_shorts,
    }
    return render(request, 'core/blogger_detail.html', context)


from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import User  # Убедись, что импорт модели верный

from django.http import HttpResponse # Добавь этот импорт



def verify_email(request, username):
    try:
        user = User.objects.get(username=username) # Проверь, ищет ли он по тому полю!
        user.is_active = True
        user.save()
        login(request, user)
        return redirect('core:dashboard') 
    except User.DoesNotExist:
        return HttpResponse(f"ОШИБКА: В базе нет пользователя с username = {username}")


# core/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Chat, Message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

import json
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import User, Chat, Message

def send_tg_feedback(tg_id, text):
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": tg_id, "text": text, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")



import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import User, Chat, Message
from .utils import get_main_menu_keyboard, get_chats_inline
import telebot

bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # --- 1. ОБРАБОТКА НАЖАТИЙ НА КНОПКИ (CallbackQuery) ---
    if 'callback_query' in data:
        call = data['callback_query']
        tg_id = call['from']['id']
        chat_id = call['data'].replace("select_chat_", "")
        
        try:
            sender = User.objects.get(tg_chat_id=tg_id)
            target_chat = Chat.objects.get(id=chat_id)
            
            # Устанавливаем активный чат для пользователя
            sender.current_tg_chat = target_chat
            sender.save()
            
            # Помечаем сообщения как прочитанные (кроме своих)
            target_chat.messages.filter(is_read=False).exclude(sender=sender).update(is_read=True)
            
            opponent = target_chat.get_opponent_name(sender)
            bot.answer_callback_query(call['id'], text=f"Выбран чат: {opponent}")
            bot.send_message(
                tg_id, 
                f"✅ Вы переключились на диалог с *{opponent}*.\nТеперь пишите сообщение — оно отправится собеседнику.", 
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard() # Убедимся, что меню на месте
            )
        except Exception as e:
            print(f"Ошибка Callback: {e}")
        
        return HttpResponse(status=200)

    # --- 2. ОБРАБОТКА СООБЩЕНИЙ (Message) ---
# --- 2. ОБРАБОТКА СООБЩЕНИЙ (Message) ---
    if 'message' not in data:
        return HttpResponse(status=200)

    message = data['message']
    tg_id = message['from']['id']
    text = message.get('text', '')

    # 1. Сначала обрабатываем /start (для всех)
    if text.startswith('/start'):
        # Логика приветствия и привязки
        bot.send_message(
            tg_id, 
            "Добро пожаловать в Flow! 🚀\nИспользуйте меню ниже для навигации.", 
            reply_markup=get_main_menu_keyboard()
        )
        return HttpResponse(status=200)

    # 2. Ищем пользователя для остальных действий
    try:
        sender = User.objects.get(tg_chat_id=tg_id)
    except User.DoesNotExist:
        bot.send_message(tg_id, "⚠️ Ваш аккаунт не привязан. Пожалуйста, авторизуйтесь через сайт.")
        return HttpResponse(status=200)

    # 3. Дальше кнопки меню (Главная, Диалоги) и пересылка...

    # РЕАКЦИЯ НА КНОПКИ МЕНЮ
    # РЕАКЦИЯ НА КНОПКИ МЕНЮ
    if text == "🏠 Главная":
        unread_count = Message.objects.filter(chat__participants=sender, is_read=False).exclude(sender=sender).count()
        # ИСКУССТВЕННОЕ ИСПРАВЛЕНИЕ: имя функции должно совпадать с импортом
        markup = get_chats_inline(sender, only_unread=True)
        
        msg = f"🏠 *Главная страница*\n\n"
        if unread_count > 0:
            msg += f"🔔 У вас {unread_count} новых сообщений в чатах ниже:"
        else:
            msg += "Новых сообщений нет."
            
        bot.send_message(tg_id, msg, parse_mode="Markdown", reply_markup=markup)
        return HttpResponse(status=200)

    if text == "📂 Мои диалоги":
        # ИСКУССТВЕННОЕ ИСПРАВЛЕНИЕ: имя функции должно совпадать с импортом
        markup = get_chats_inline(sender)
        bot.send_message(tg_id, "Выберите диалог из списка:", reply_markup=markup)
        return HttpResponse(status=200)

    # ПЕРЕСЫЛКА СООБЩЕНИЯ (если чат выбран)
    if text and not text.startswith('/'):
        if sender.current_tg_chat:
            chat = sender.current_tg_chat
            
            # Сохраняем в БД
            Message.objects.create(chat=chat, sender=sender, text=text, is_from_tg=True)
            
            # Пересылаем админам/в топик
            if chat.telegram_topic_id:
                bot.send_message(
                    settings.TELEGRAM_ADMIN_GROUP_ID, 
                    text, 
                    message_thread_id=chat.telegram_topic_id
                )
            # (Опционально) Отправка через WebSocket на сайт
            # ... код с channel_layer ...
        else:
            bot.send_message(tg_id, "❌ У вас не выбран активный чат. Выберите его в '📂 Мои диалоги'.")

    return HttpResponse(status=200)

from django.shortcuts import render, get_object_or_404
from .models import ProductAd

def product_detail(request, pk):
    product = get_object_or_404(ProductAd, pk=pk) # ИСПРАВЛЕНО
    
    # Также проверь фильтры внутри этой функции, если они есть:
    similar_products = ProductAd.objects.filter(category=product.category).exclude(pk=pk)[:4]
    
    return render(request, 'core/product_detail.html', {
    'product': product,
    'ad': product,  # <--- Добавь эту строку
    'similar_products': similar_products,
})

@login_required
def chat_room_by_id(request, chat_id):
    """
    Вспомогательный роут, чтобы заходить в чат по ID самого чата, 
    а не по ID собеседника. Удобно для ссылок из Telegram.
    """
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    # Находим второго участника, чтобы перенаправить на стандартный chat_detail
    other_user = chat.participants.exclude(id=request.user.id).first()
    
    if other_user:
        return redirect('core:chat_detail', user_id=other_user.id)
    
    return redirect('core:chat_list')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import User
import json

@csrf_exempt
def connect_telegram_api(request):
    if request.method == "POST":
        secret_key = request.POST.get("secret_key")
        if secret_key != "MySuperSecretKey123":
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

        user_id = request.POST.get("user_id")
        tg_id = request.POST.get("telegram_id")

        try:
            # Ищем напрямую в модели User
            user = User.objects.get(id=user_id)
            user.tg_chat_id = tg_id  # Твоё поле из models.py
            user.save()
            return JsonResponse({"status": "success"})
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"}, status=404)
    return JsonResponse({"status": "error"}, status=400)


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        # Собираем словарь из формы
        labels = request.POST.getlist('custom_label[]')
        values = request.POST.getlist('custom_value[]')
        new_custom_data = {l.strip(): v.strip() for l, v in zip(labels, values) if l.strip() and v.strip()}

        if user.role == 'blogger':
            # Достаем профиль блогера
            profile = user.blogger_profile 
            profile.inn = request.POST.get('inn')
            profile.bik = request.POST.get('bik')
            profile.account_number = request.POST.get('account_number')
            profile.channel_link = request.POST.get('channel_link')
            profile.channel_description = request.POST.get('channel_description')
            profile.bank_receiver = request.POST.get('bank_receiver')
            profile.custom_data = new_custom_data # Сохраняем в профиль!
            profile.save()
        else:
            # Достаем профиль рекламодателя
            profile = user.advertiser_profile
            profile.inn = request.POST.get('inn')
            profile.bik = request.POST.get('bik')
            profile.account_number = request.POST.get('account_number')
            profile.company_name = request.POST.get('company_name')
            profile.legal_address = request.POST.get('legal_address')
            profile.website = request.POST.get('website')
            profile.ogrn = request.POST.get('ogrn')
            profile.custom_data = new_custom_data # Сохраняем в профиль!
            profile.save()

        messages.success(request, "Профиль успешно обновлен!")
        return redirect('core:dashboard')
from django.shortcuts import render
from django.contrib.auth import get_user_model

User = get_user_model()

def blogger_list(request):
    from .models import BloggerProfile
    
    # Получаем все профили блогеров
    # Мы используем select_related, чтобы Django не делал 100 запросов к базе
    bloggers = BloggerProfile.objects.select_related('user').all()
    
    return render(request, 'core/blogger_list.html', {
        'bloggers': bloggers
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import BloggerProfile, ProductAd  # Используем ПРАВИЛЬНЫЕ имена моделей

User = get_user_model()

def blogger_list(request):
    """
    Список блогеров для маркетплейса.
    """
    # select_related('user') подтягивает данные из таблицы User за один запрос
    bloggers = BloggerProfile.objects.select_related('user').all()
    
    return render(request, 'core/blogger_list.html', {
        'bloggers': bloggers
    })

def marketplace(request):
    """
    Общий маркетплейс объявлений (Ad List).
    """
    # ИСПРАВЛЕНО: используем ProductAd вместо Product
    ads = ProductAd.objects.filter(is_active=True).order_by('-created_at') 
    
    return render(request, 'core/ad_list.html', {
        'ads': ads
    })

@login_required

def manage_products(request):
    """
    Личный кабинет рекламодателя (My Ads).
    """
    # 1. Проверяем, есть ли у пользователя профиль рекламодателя
    if hasattr(request.user, 'advertiser_profile'):
        # 2. Фильтруем объявления по профилю
        # Убедитесь, что поле в модели ProductAd называется 'advertiser'
        user_ads = ProductAd.objects.filter(advertiser=request.user.advertiser_profile).order_by('-created_at')
    else:
        user_ads = ProductAd.objects.none()

    # 3. Передаем в шаблон именно под именем 'ads'
    return render(request, 'core/my_ads.html', {
        'ads': user_ads,  # Это имя должно совпадать с циклом {% for ad in ads %}
    })
@login_required
def my_ads_view(request):
    # Если в модели ProductAd поле называется advertiser (связь с AdvertiserProfile)
    if hasattr(request.user, 'advertiser_profile'):
        user_ads = ProductAd.objects.filter(advertiser=request.user.advertiser_profile)
    else:
        user_ads = ProductAd.objects.none()
    
    return render(request, 'core/my_ads.html', {
        'ads': user_ads,  # Важно: имя должно быть 'ads' для вашего шаблона!
    })
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
@login_required
def edit_profile(request):
    """
    Редактирование профиля блогера и прайс-листа.
    """
    profile = getattr(request.user, 'blogger_profile', None)

    if not profile:
        messages.error(request, "У вас нет профиля блогера.")
        return redirect('core:home')

    if request.method == 'POST':
        try:
            profile.price_start = request.POST.get('price_start') or 0
            profile.price_middle = request.POST.get('price_middle') or 0
            profile.price_end = request.POST.get('price_end') or 0
            profile.price_shorts = request.POST.get('price_shorts') or 0
            profile.save()
            messages.success(request, "Прайс-лист успешно обновлен!")
            return redirect('core:edit_profile') 
        except Exception as e:
            messages.error(request, f"Ошибка при сохранении: {e}")

    return render(request, 'core/edit_profile.html', {'profile': profile})
