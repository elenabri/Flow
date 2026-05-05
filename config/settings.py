import os
import dj_database_url
from pathlib import Path

# --- ОСНОВНЫЕ ПУТИ ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- БЕЗОПАСНОСТЬ ---
SECRET_KEY = 'django-insecure-q(cs0^v-hof)#h-ql#774!$02yi%6j28(bud4xtc%sv9h-$l$u'
DEBUG = False 
ALLOWED_HOSTS = ['*']  # Позже замени на ['tubeflow-mvfo.onrender.com', '127.0.0.1']

# --- ПРИЛОЖЕНИЯ ---
INSTALLED_APPS = [
    'daphne',
    'channels',
    'core',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]
ASGI_APPLICATION = 'config.asgi.application'

# Настройка твоего платного Redis (возьми URL из настроек Render)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Для статики на Render
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
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'core' / 'templates',
        ],
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

WSGI_APPLICATION = 'config.wsgi.application'

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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- ИНТЕРНАЦИОНАЛИЗАЦИЯ ---
LANGUAGE_CODE = 'ru-ru'  # Поставил русский по умолчанию
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# --- СТАТИКА И МЕДИА ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    # BASE_DIR / 'static',  <-- Закомментируй это, если папка в корне пустая
    BASE_DIR / 'core' / 'static', # Оставь только путь к реальным файлам
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise для работы статики на хостинге
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- ПОЧТА (SMTP Gmail) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True   # Именно TLS для 587 порта
EMAIL_USE_SSL = False  # SSL должен быть False
EMAIL_HOST_USER = 'len.bri14@gmail.com'
EMAIL_HOST_PASSWORD = 'yvyojptzikbylojr'
DEFAULT_FROM_EMAIL = 'Vkusnevich <len.bri14@gmail.com>'
TELEGRAM_BOT_TOKEN = "8275098246:AAG0GwVR8FNSS7DhnmhCseZZwzXvO1h-n7k"

# --- ПЕРЕЙТИ ПОСЛЕ ВХОДА ---
LOGIN_REDIRECT_URL = 'core:login_router'
LOGOUT_REDIRECT_URL = 'login'

# --- ПРОЧИЕ НАСТРОЙКИ ---
PASSWORD_RESET_TIMEOUT = 14400
SITE_DOMAIN = 'tubeflow-mvfo.onrender.com'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CSRF_TRUSTED_ORIGINS = [
    "https://tubeflow-mvfo.onrender.com",
    "https://*.onrender.com"  # Это на случай, если домен чуть изменится
]
ALLOWED_HOSTS = ["tubeflow-mvfo.onrender.com", "localhost", "127.0.0.1"]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
