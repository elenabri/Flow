import os
import dj_database_url
from pathlib import Path

# --- ОСНОВНЫЕ ПУТИ ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- БЕЗОПАСНОСТЬ ---
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key')
DEBUG = False 
ALLOWED_HOSTS = ["tubeflow-mvfo.onrender.com", "localhost", "127.0.0.1"]

# --- ПРИЛОЖЕНИЯ ---
INSTALLED_APPS = [
    'daphne',
    'channels',
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'cloudinary',
    'core',
]

ASGI_APPLICATION = 'config.asgi.application'
WSGI_APPLICATION = 'config.wsgi.application'

# --- REDIS / CHANNELS ---
# Если на Render есть Redis, замени 'InMemoryChannelLayer' на 'RedisChannelLayer'
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Сразу после Security
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# --- ШАБЛОНЫ ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.unread_messages_count',
            ],
        },
    },
]

# --- БАЗА ДАННЫХ ---
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# --- ПОЛЬЗОВАТЕЛИ ---
AUTH_USER_MODEL = 'core.User'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

# --- ИНТЕРНАЦИОНАЛИЗАЦИЯ ---
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# --- СТАТИКА И МЕДИА ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Убедитесь, что папка 'static' находится ВНУТРИ папки 'core'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core', 'static'),
]

# Настройка WhiteNoise (убрал Manifest, чтобы избежать 404 при отсутствии файлов)
SSTATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

# Настройка Cloudinary для Медиа
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET')
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- ПОЧТА (SMTP Gmail) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'len.bri14@gmail.com'
EMAIL_HOST_PASSWORD = 'yvyojptzikbylojr' # Рекомендую заменить на переменную окружения
DEFAULT_FROM_EMAIL = 'Vkusnevich <len.bri14@gmail.com>'

# --- TELEGRAM ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k")
TELEGRAM_ADMIN_GROUP_ID = os.getenv('TELEGRAM_ADMIN_GROUP_ID')

# --- ПРОЧИЕ НАСТРОЙКИ ---
LOGIN_REDIRECT_URL = 'core:login_router'
LOGOUT_REDIRECT_URL = 'login'
SITE_DOMAIN = 'tubeflow-mvfo.onrender.com'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CSRF_TRUSTED_ORIGINS = [
    "https://tubeflow-mvfo.onrender.com",
    "https://*.onrender.com"
]
WHITENOISE_ROOT = BASE_DIR / 'staticfiles'
