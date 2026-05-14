import requests
import re
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from .constants import TOPIC_CHOICES
from django.db.models import JSONField


# --- ПОЛЬЗОВАТЕЛЬ ---

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('blogger', 'Блогер'),
        ('advertiser', 'Рекламодатель'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='blogger')
    email = models.EmailField(unique=True)

    # Поле для привязки Telegram (чтобы знать, кому слать уведомления)


    telegram_handle = models.CharField(
        "Ник в Telegram", 
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Ник пользователя без символа @"
    )

    # Оставляем ваш существующий tg_chat_id для уведомлений бота
    tg_chat_id = models.BigIntegerField(null=True, blank=True)
    
    

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    # СТРОКУ current_tg_chat_id = models.IntegerField(...) УДАЛЯЕМ!


# --- ПРОФИЛЬ БЛОГЕРА ---
class BloggerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='blogger_profile')
    channel_name = models.CharField("Название канала", max_length=255)
    channel_link = models.URLField("Ссылка на канал")
    channel_description = models.TextField("Описание", blank=True)
    subscribers_count = models.PositiveIntegerField(default=0, verbose_name="Подписчиков")
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    banner_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="Баннер канала")
    
    # Статистика
    median_views = models.PositiveIntegerField(default=0, verbose_name="Медиана просмотров (Long)")
    median_views_shorts = models.PositiveIntegerField(default=0, verbose_name="Медиана просмотров (Shorts)")

    # Прайс-лист
    price_start = models.DecimalField("Интеграция в начале", max_digits=10, decimal_places=2, default=0)
    price_middle = models.DecimalField("Интеграция в середине", max_digits=10, decimal_places=2, default=0)
    price_end = models.DecimalField("Интеграция в конце", max_digits=10, decimal_places=2, default=0)
    price_shorts = models.DecimalField("Цена за Shorts", max_digits=10, decimal_places=2, default=0)
    
    categories = models.CharField("Тематики", max_length=500) 
    

    # Реквизиты для выплат
    bank_receiver = models.CharField("ФИО получателя", max_length=255, blank=True)
    inn = models.CharField("ИНН", max_length=12, blank=True)
    bik = models.CharField("БИК", max_length=9, blank=True)
    account_number = models.CharField("Расчетный счет", max_length=20, blank=True)
    
    # Сюда будут сохраняться динамические поля из JS
    custom_data = JSONField("Доп. поля", default=dict, blank=True)

    # Логика сокращения категорий (для карточки)
    def get_short_categories(self):
        if not self.categories:
            return "Без категории"
        choices_dict = dict(TOPIC_CHOICES)
        # Очищаем от подкатегорий после '|' и разбиваем
        main_part = self.categories.split('|')[0]
        cats = [choices_dict.get(c.strip(), c.strip()) for c in main_part.split(',') if c.strip()]
        if len(cats) > 2:
            return f"{cats[0]}, {cats[1]} и др."
        return ", ".join(cats)

    # Полный перевод для детальной страницы
    def get_categories_russian(self):
        if not self.categories:
            return ""
        choices_dict = dict(TOPIC_CHOICES)
        raw_list = [c.strip() for c in self.categories.split(',')]
        russian_list = [choices_dict.get(c, c) for c in raw_list]
        return ", ".join(russian_list)

    @property
    def price_long_min(self):
        # Собираем все цены за длинные видео
        prices = [self.price_start, self.price_middle, self.price_end]
        # Оставляем только те, что больше нуля
        valid_prices = [p for p in prices if p and p > 0]
        return min(valid_prices) if valid_prices else 0

    @property
    def display_cpv_long(self):
        """Цена за 1 просмотр (Long) с точностью 1 знак"""
        if self.median_views > 0 and self.price_long_min > 0:
            # Считаем: минимальная цена / медианные просмотры
            val = float(self.price_long_min) / self.median_views
            return round(val, 1)
        return 0

    @property
    def display_cpv_shorts(self):
        """Цена за 1 просмотр (Shorts) с точностью 1 знак"""
        if self.median_views_shorts > 0 and self.price_shorts > 0:
            val = float(self.price_shorts) / self.median_views_shorts
            return round(val, 1)
        return 0
    
    def __str__(self):
        return f"Блогер: {self.channel_name} (@{self.user.username})"


# --- ПРОФИЛЬ РЕКЛАМОДАТЕЛЯ ---
class AdvertiserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='advertiser_profile')
    company_name = models.CharField("Название компании", max_length=255)
    legal_address = models.CharField("Юр. адрес", max_length=500, blank=True)
    website = models.URLField("Сайт", blank=True)
    
    # Реквизиты
    inn = models.CharField("ИНН", max_length=12, blank=True)
    bik = models.CharField("БИК", max_length=9, blank=True)
    account_number = models.CharField("Расчетный счет", max_length=20, blank=True)
    ogrn = models.CharField("ОГРН", max_length=15, blank=True)
    
    # Сюда будут сохраняться динамические поля из JS
    custom_data = JSONField("Доп. поля", default=dict, blank=True)

    def __str__(self):
        return self.company_name


# --- ОБЪЯВЛЕНИЕ ТОВАРА (Маркетплейс) ---
class ProductAd(models.Model):
    advertiser = models.ForeignKey(AdvertiserProfile, on_delete=models.CASCADE, related_name='ads')
    
    name = models.CharField("Название", max_length=200) 
    short_description = models.TextField(verbose_name="Краткое описание", max_length=30, blank=True)
    additional_info = models.TextField(verbose_name="Доп. информация", blank=True)
    is_barter = models.BooleanField(verbose_name="Только бартер", default=True)
    description = models.TextField("Описание и ТЗ")
    category = models.CharField("Категории (через запятую)", max_length=500)
    
    # Изображения
    image = models.ImageField("Файл фото", upload_to='products/%Y/%m/%d/', blank=True, null=True)
    avatar_url = models.URLField("Ссылка на фото", blank=True, null=True, max_length=500)
    
    # Ссылки
    link_wb = models.URLField("Wildberries", max_length=500, null=True, blank=True)
    link_ozon = models.URLField("Ozon", max_length=500, null=True, blank=True)
    link_other = models.URLField("Сайт/Другое", max_length=500, null=True, blank=True)
    
    is_active = models.BooleanField("Опубликовать", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Объявление товара"
        verbose_name_plural = "Объявления товаров"
        ordering = ['-created_at']

    # ПОЛЕЗНО: Автоматический выбор доступного фото для шаблона
    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        elif self.avatar_url:
            return self.avatar_url
        return "/static/img/no-image.png" # Путь к заглушке

    def get_short_categories(self):
        if not self.category:
            return "Без категории"
        try:
            # Импортируем внутри, если TOPIC_CHOICES в другом файле

            choices_dict = dict(TOPIC_CHOICES)
            cats = [choices_dict.get(c.strip(), c.strip()) for c in self.category.split(',') if c.strip()]
        except (NameError, ImportError):
            cats = [c.strip() for c in self.category.split(',') if c.strip()]
            
        if len(cats) > 2:
            return f"{cats[0]}, {cats[1]} и др."
        return ", ".join(cats)

    def __str__(self):
        company = getattr(self.advertiser, 'company_name', 'Рекламодатель')
        return f"{self.name} ({company})"
# --- ЧАТЫ ---
class Chat(models.Model):
    participants = models.ManyToManyField(User, related_name='chats')
    ad = models.ForeignKey(ProductAd, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, default="Диалог")
    telegram_topic_id = models.IntegerField(null=True, blank=True)

    # Вспомогательный метод, чтобы бот знал, как назвать собеседника
    def get_opponent_name(self, current_user):
        opponent = self.participants.exclude(id=current_user.id).first()
        if not opponent:
            return "Неизвестный"
        
        # Если собеседник — рекламодатель, берем название компании
        if hasattr(opponent, 'advertiser_profile'):
            return opponent.advertiser_profile.company_name
        # Если блогер — название канала
        if hasattr(opponent, 'blogger_profile'):
            return opponent.blogger_profile.channel_name
        
        return opponent.username

class Message(models.Model):
    # Делаем чат обязательным
    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_from_tg = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
# --- КОНТРАКТЫ ---
class AdContract(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создан'),
        ('paid', 'Оплачен (Заморожено)'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    number = models.CharField("Номер договора", max_length=50, unique=True)
    advertiser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adv_contracts')
    blogger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogger_contracts')
    total_amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Договор"
        verbose_name_plural = "Договоры"

    def __str__(self):
        return f"Договор {self.number}"


# --- ЭТАПЫ (РОЛИКИ) ---
class VideoItem(models.Model):
    VIDEO_STATUS = [
        ('in_progress', 'В работе'),
        ('review', 'На утверждении'),
        ('correction', 'На доработке'),
        ('approved', 'Утвержден'),
        ('released', 'Выпущен'),
    ]
    
    contract = models.ForeignKey(AdContract, on_delete=models.CASCADE, related_name='videos')
    format = models.CharField("Формат", max_length=50)
    deadline = models.DateField("Дедлайн")
    status = models.CharField(max_length=20, choices=VIDEO_STATUS, default='in_progress')
    
    video_link = models.URLField("Ссылка на видео", blank=True, null=True)
    time_start = models.CharField("Начало рекламы", max_length=10, blank=True)
    time_end = models.CharField("Конец рекламы", max_length=10, blank=True)

    class Meta:
        verbose_name = "Ролик"
        verbose_name_plural = "Ролики"

    def __str__(self):
        return f"{self.format} для {self.contract.number}"


# --- ПОДДЕРЖКА ---
class SupportTicket(models.Model):
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"От {self.email} - {self.created_at.strftime('%d.%m %H:%M')}"


from django.db import models
from django.utils import timezone
from datetime import timedelta

class AdIntegration(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    youtube_url = models.URLField(verbose_name="Ссылка на ролик")
    timestamp = models.IntegerField(default=0)
    product_name = models.CharField(max_length=255, blank=True, verbose_name="Товар")
    brand = models.CharField(max_length=255, blank=True, verbose_name="Бренд")
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Стоимость")
    
    # Данные из API
    channel_name = models.CharField(max_length=255, blank=True)
    publish_date = models.DateTimeField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(null=True, blank=True)
  
    def can_update_views(self):
        """Проверка: можно ли обновлять данные (раз в 7 дней или если данных еще нет)"""
        if not self.last_updated:
            return True
        return timezone.now() > self.last_updated + timedelta(days=7)

    def extract_video_id(self):
        """Извлекает ID видео из ссылки YouTube"""
        regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        match = re.search(regex, self.youtube_url)
        return match.group(1) if match else None

    def update_youtube_data(self):
        """Запрашивает данные с YouTube API с учетом лимита в одну неделю"""
        if not self.can_update_views():
            print(f"Обновление отклонено: неделя еще не прошла для {self.id}")
            return False

        video_id = self.extract_video_id()
        if not video_id:
            return False

        api_key = "AIzaSyBIQSgM6nAcLnt5En1E59Ee65jL-NHTJDs"
        url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=statistics,snippet"
        
        try:
            response = requests.get(url).json()
            if 'items' in response and response['items']:
                item = response['items'][0]
                self.views = int(item['statistics'].get('viewCount', 0))
                self.channel_name = item['snippet'].get('channelTitle', '')
                self.publish_date = item['snippet'].get('publishedAt')
                self.last_updated = timezone.now()
                self.save(update_fields=['views', 'channel_name', 'publish_date', 'last_updated'])
                return True
        except Exception as e:
            print(f"Ошибка API: {e}")
        return False

    def save(self, *args, **kwargs):
        """
        При первом сохранении (создании) данные подтянутся сразу.
        При последующих изменениях (через админку) — только если вызовете метод отдельно.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.update_youtube_data()

    @property
    def cpv(self):
        if self.cost and self.views and self.views > 0:
            return round(self.cost / self.views, 2)
        return 0

    @property
    def formatted_timestamp(self):
        if self.timestamp:
            mins = self.timestamp // 60
            secs = self.timestamp % 60
            return f"{mins}:{secs:02d}"
        return "0:00"
