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

# Твои локальные файлы
from .forms import RegistrationForm, EmailLoginForm
from .models import (
    BloggerProfile, AdvertiserProfile, ProductAd, 
    Message, AdContract, SupportTicket
)
from .constants import TOPIC_CHOICES, SUB_TOPICS_MAP

User = get_user_model()
YOUTUBE_API_KEY = 'AIzaSyBIQSgM6nAcLnt5En1E59Ee65jL-NHTJDs'

# --- 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def parse_duration_to_seconds(duration):
    match = re.search(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match: return 0
    d, h, m, s = [int(x) if x else 0 for x in match.groups()]
    return d * 86400 + h * 3600 + m * 60 + s

def get_youtube_stats(channel_url, api_key):
    handle_match = re.search(r'@([\w\.-]+)', channel_url)
    if not handle_match: return None
    handle = handle_match.group(1)
    try:
        ch_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails,brandingSettings&forHandle={handle}&key={api_key}"
        ch_data = requests.get(ch_url, timeout=7).json()
        if not ch_data.get("items"): return None
        item = ch_data["items"][0]
        uploads_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        v_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_id}&maxResults=50&key={api_key}"
        v_ids = [v["contentDetails"]["videoId"] for v in requests.get(v_url).json().get("items", [])]
        
        long_views, shorts_views = [], []
        if v_ids:
            stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,statistics&id={','.join(v_ids)}&key={api_key}"
            for v in requests.get(stats_url).json().get("items", []):
                views = int(v["statistics"].get("viewCount", 0))
                if parse_duration_to_seconds(v["contentDetails"]["duration"]) <= 200:
                    shorts_views.append(views)
                else:
                    long_views.append(views)

        return {
            'name': item["snippet"]["title"], 
            'subs': int(item["statistics"].get("subscriberCount", 0)),
            'avatar': item["snippet"]["thumbnails"]["high"]["url"],
            'banner': item.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl"),
            'long_median': int(statistics.median(long_views)) if long_views else 0,
            'shorts_median': int(statistics.median(shorts_views)) if shorts_views else 0,
        }
    except: return None

def send_verification_email(user, password): # Добавили password
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"http://127.0.0.1:8000/activate/{uid}/{token}" 
    
    context = {
        'user': user, 
        'link': link, 
        'temp_password': password # Передаем в шаблон письма
    }
    html_message = render_to_string('registration/verify_email.html', context)
    
    send_mail(
        "Подтвердите ваш Email — Vkusnevich",
        f"Ваш пароль: {password}. Ссылка для активации: {link}", # Текстовая версия
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message
    )

# --- 2. АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ---
from django.shortcuts import redirect
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # 1. Создаем объект пользователя, но не сохраняем в БД сразу
            user = form.save(commit=False)
            user.email = form.cleaned_data.get('email')
            user.username = user.email  # Используем email как login
            
            # 2. Генерируем пароль ОДИН раз и сразу хешируем
            pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user.set_password(pwd)
            
            # 3. Деактивируем до подтверждения почты
            user.is_active = False 
            user.save()

            # 4. Создаем профили (блогер или рекламодатель)
            role = form.cleaned_data.get('role')
            try:
                if role == 'blogger':
                    BloggerProfile.objects.create(
                        user=user,
                        channel_name=request.POST.get('api_channel_name'),
                        channel_link=form.cleaned_data.get('channel_link'),
                        subscribers_count=int(request.POST.get('api_subs') or 0),
                        median_views=int(request.POST.get('api_long_median') or 0),
                        median_views_shorts=int(request.POST.get('api_shorts_median') or 0),
                        categories=", ".join(form.cleaned_data.get('topics') or []),
                        price_start=form.cleaned_data.get('price_start') or 0,
                        avatar_url=request.POST.get('api_avatar'),
                        banner_url=request.POST.get('api_banner'),
                    )
                elif role == 'advertiser':
                    adv = AdvertiserProfile.objects.create(
                        user=user, 
                        company_name=request.POST.get('company_name')
                    )
                    if request.POST.get('title'):
                        ProductAd.objects.create(
                            advertiser=adv, 
                            title=request.POST.get('title'), 
                            product_image=request.FILES.get('product_image'),
                            category=", ".join(request.POST.getlist('topics')),
                            link_wb=request.POST.get('link_wb'),
                            link_ozon=request.POST.get('link_ozon'),
                            description=request.POST.get('description')
                        )

                # 5. ОТПРАВКА ПИСЬМА (передаем и пользователя, и "сырой" пароль)
                send_verification_email(user, pwd)
                
                return render(request, 'core/success.html', {
                    'email': user.email, 
                    'password': pwd,
                    'message': 'Инструкции по активации отправлены на ваш Email.'
                })

            except Exception as e:
                # Если почта не ушла, пользователь уже в базе, но не активен. 
                # Можно вывести ошибку или логировать её.
                messages.error(request, f"Ошибка при отправке письма: {e}")
                return render(request, 'core/success.html', {'email': user.email, 'password': pwd})
                
    else:
        form = RegistrationForm()
        
    return render(request, 'core/register.html', {
        'form': form, 
        'sub_topics_json': json.dumps(SUB_TOPICS_MAP), 
        'TOPIC_CHOICES': TOPIC_CHOICES
    })

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except: user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        # АВТОВХОД: после клика по ссылке он уже внутри системы
        login(request, user) 
        
        messages.success(request, "Аккаунт успешно активирован!")
        return redirect('core:dashboard') # Или ваш login_router
    
    return render(request, 'core/activation_invalid.html')

def user_login(request):
    if request.method == 'POST':
        form = EmailLoginForm(data=request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password'))
            if user and user.is_active:
                login(request, user)
                return redirect('core:marketplace')
    return render(request, 'registration/login.html', {'form': EmailLoginForm()})

# --- 3. МАРКЕТПЛЕЙС И ДЕТАЛИ ---

from django.shortcuts import render
from django.db.models import Q
from .models import BloggerProfile, ProductAd  # Исправленные имена моделей
from .constants import TOPIC_CHOICES

def marketplace(request):
    # 1. Получаем базовые параметры
    active_tab = request.GET.get('tab', 'ads')
    query = request.GET.get('q', '')
    selected_cats = request.GET.getlist('cat')
    
    # 2. Инициализируем QuerySets
    bloggers = BloggerProfile.objects.all()
    ads = ProductAd.objects.filter(is_active=True)

    # 3. Поиск по тексту
    if query:
        ads = ads.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) | 
            Q(advertiser__company_name__icontains=query)
        )
        bloggers = bloggers.filter(
            Q(channel_name__icontains=query) | 
            Q(categories__icontains=query)
        )

    # 4. Фильтр по категориям
    if selected_cats:
        ad_cat_queries = Q()
        blog_cat_queries = Q()
        for cat in selected_cats:
            ad_cat_queries |= Q(category__icontains=cat)
            blog_cat_queries |= Q(categories__icontains=cat)
        ads = ads.filter(ad_cat_queries)
        bloggers = bloggers.filter(blog_cat_queries)

    # 5. Специфические фильтры
    if active_tab == 'bloggers':
        # Подписчики
        subs_min = request.GET.get('subs_min')
        subs_max = request.GET.get('subs_max')
        if subs_min:
            bloggers = bloggers.filter(subscribers_count__gte=subs_min)
        if subs_max:
            bloggers = bloggers.filter(subscribers_count__lte=subs_max)

        # Цена
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        if price_min:
            bloggers = bloggers.filter(price_start__gte=price_min)
        if price_max:
            bloggers = bloggers.filter(price_start__lte=price_max)

        # Сортировка
        sort_blog = request.GET.get('sort_blog', '-subscribers_count')
        # Если сортировка по CPV, используем property или аннотацию (здесь простая по подпискам)
        if sort_blog in ['-subscribers_count', 'subscribers_count', '-median_views']:
            bloggers = bloggers.order_by(sort_blog)

    else:  # Вкладка товаров (ads)
        budget_min = request.GET.get('budget_min')
        budget_max = request.GET.get('budget_max')
        if budget_min:
            ads = ads.filter(budget__gte=budget_min)
        if budget_max:
            ads = ads.filter(budget__lte=budget_max)
        
        ads = ads.order_by('-created_at')

    context = {
        'active_tab': active_tab,
        'query': query,
        'selected_cats': selected_cats,
        'bloggers': bloggers,
        'ads': ads,
        'TOPIC_CHOICES': TOPIC_CHOICES,
    }
    return render(request, 'core/marketplace.html', context)
def product_detail(request, pk):
    ad = get_object_or_404(ProductAd, pk=pk)
    return render(request, 'core/product_detail.html', {'ad': ad})

# --- 4. ЧАТ И РАССЫЛКА ---

@login_required
def chat_list(request):
    msgs = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
    chats = { (m.receiver if m.sender == request.user else m.sender): m for m in msgs }
    return render(request, 'core/chat_list.html', {'chats': chats})

@login_required
def chat_detail(request, chat_id):
    other = get_object_or_404(User, id=chat_id)
    if request.method == 'POST':
        txt = request.POST.get('text')
        if txt: Message.objects.create(sender=request.user, receiver=other, text=txt)
    msgs = Message.objects.filter((Q(sender=request.user) & Q(receiver=other)) | (Q(sender=other) & Q(receiver=request.user))).order_by('created_at')
    return render(request, 'core/chat_detail.html', {'other_user': other, 'chat_messages': msgs})

@login_required
def bulk_message_setup(request):
    if request.method == 'POST':
        txt = request.POST.get('message')
        cat = request.POST.get('category_filter')
        bloggers = BloggerProfile.objects.all()
        if cat and cat != 'all': bloggers = bloggers.filter(categories__icontains=cat)
        for b in bloggers:
            if b.user != request.user:
                Message.objects.create(sender=request.user, receiver=b.user, text=f"[РАССЫЛКА] {txt}")
        messages.success(request, "Рассылка завершена!")
        return redirect('chat_list')
    return render(request, 'core/bulk_message_setup.html', {'TOPIC_CHOICES': TOPIC_CHOICES})

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import ProductAd, Message

@login_required
def send_response(request, ad_id):
    # 1. Получаем товар, на который блогер хочет откликнуться
    ad = get_object_or_404(ProductAd, id=ad_id)
    
    # 2. Проверяем, не является ли сам пользователь рекламодателем этого товара
    if ad.advertiser.user == request.user:
        messages.warning(request, "Вы не можете откликнуться на собственный товар.")
        return redirect('core:dashboard')

    # 3. Создаем сообщение для рекламодателя
    # Заменили ad.title на ad.name, чтобы избежать AttributeError
    Message.objects.create(
        sender=request.user, 
        receiver=ad.advertiser.user, 
        text=f"Новый отклик на ваш товар: «{ad.name}». Блогер готов к сотрудничеству!"
    )
    
    # 4. Уведомляем пользователя об успехе
    messages.success(request, f"Ваш отклик на товар «{ad.name}» успешно отправлен!")
    
    # 5. Перенаправляем в список чатов или обратно на маркетплейс
    return redirect('core:chat_list')

# --- 5. УПРАВЛЕНИЕ И ПРОФИЛЬ ---

@login_required
def manage_products(request):
    adv = get_object_or_404(AdvertiserProfile, user=request.user)
    if request.method == 'POST':
        ProductAd.objects.create(advertiser=adv, title=request.POST.get('title'), category=request.POST.get('category'), image=request.FILES.get('product_image'))
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

def fetch_youtube_data(request):
    return JsonResponse(get_youtube_stats(request.GET.get('url'), YOUTUBE_API_KEY) or {'error': '404'}, safe=False)

@csrf_exempt
def support_ajax(request):
    if request.method == "POST":
        SupportTicket.objects.create(email=request.POST.get('email'), message=request.POST.get('message'))
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

def home(request): return render(request, 'core/index.html')


# --- 7. ПАНЕЛИ УПРАВЛЕНИЯ (DASHBOARDS) ---


@login_required
def dashboard(request):
    user = request.user
    
    if request.method == 'POST':
        if hasattr(user, 'blogger_profile'):
            # Обновление прайса для блогера
            profile = user.blogger_profile
            # Используем .get(..., 0) и приводим к числу, чтобы избежать ошибок в базе
            profile.price_start = request.POST.get('price_start', 0)
            profile.price_middle = request.POST.get('price_middle', 0)
            profile.price_end = request.POST.get('price_end', 0) # Исправили с .end на .price_end
            profile.price_shorts = request.POST.get('price_shorts', 0)
            profile.save()
            messages.success(request, "Прайс-лист успешно обновлен")
        
        elif hasattr(user, 'advertiser_profile'):
            # Добавление товара для Вкусневич (исправляем TypeError)
            ProductAd.objects.create(
                advertiser=user.advertiser_profile,
                name=request.POST.get('name'),           # Новое название поля в модели
                category=request.POST.get('category'),   # Категории
                description=request.POST.get('description'),
                link_wb=request.POST.get('link_wb'),     # Новые поля ссылок
                link_ozon=request.POST.get('link_ozon'),
                link_other=request.POST.get('link_other'),
                image=request.FILES.get('product_image'), # Обработка файла
                avatar_url=request.POST.get('avatar_url') # Ссылка на фото
            )
            messages.success(request, "Товар успешно добавлен в маркетплейс")
            
        return redirect('core:dashboard')

    # Сбор данных для отображения (GET)
    context = {}
    
    if hasattr(user, 'blogger_profile'):
        context['profile'] = user.blogger_profile
        context['recent_messages'] = Message.objects.filter(receiver=user).order_by('-created_at')[:5]
        context['active_contracts'] = AdContract.objects.filter(blogger=user).exclude(status='completed')
        return render(request, 'core/dashboard.html', context)
    
    elif hasattr(user, 'advertiser_profile'):
        context['profile'] = user.advertiser_profile
        # Используем 'products', так как в шаблоне прописано {% for product in products %}
        context['products'] = ProductAd.objects.filter(advertiser=user.advertiser_profile).order_by('-created_at')
        context['active_contracts'] = AdContract.objects.filter(advertiser=user).exclude(status='completed')
        return render(request, 'core/dashboard.html', context)
    
    # Если у пользователя нет профиля (редкий случай), просто рендерим пустой шаблон или редирект
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
        
    return render(request, 'core/edit_blogger_profile.html', {
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
