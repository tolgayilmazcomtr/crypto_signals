"""
Django settings for crypto_signals project.

Generated by 'django-admin startproject' using Django 4.2.8.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*mrrkgm$lfwt6^2mfgr1(j!)r7)n^*l2j9&_agy_5l+27f2%27'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'signals',  
    'rest_framework',
    'background_task',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'crypto_signals.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'signals' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crypto_signals.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_L10N = True
USE_TZ = True



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Parite ikonları için özel klasör
PAIR_ICONS_DIR = MEDIA_ROOT / 'pair_icons'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'signals.CustomUser'
LOGIN_URL = 'signals:login'
LOGIN_REDIRECT_URL = 'signals:trade-signal'
LOGOUT_REDIRECT_URL = 'signals:logout_done'

# settings.py

from django.contrib.messages import constants as messages

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',  # Bootstrap uyumlu hata mesajları için
}

# Channels
ASGI_APPLICATION = 'crypto_signals.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Authentication settings
LOGIN_URL = 'signals:login'
LOGIN_REDIRECT_URL = 'signals:trade-signal'
LOGOUT_REDIRECT_URL = 'signals:logout_done'

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 saat
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# E-posta ayarları - Hostinger SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.hostinger.com'
EMAIL_PORT = 465  # SSL için 465 portu
EMAIL_USE_SSL = True  # SSL kullanımı
EMAIL_USE_TLS = False  # SSL kullanıyoruz, TLS değil
EMAIL_HOST_USER = 'info@torypto.com'
EMAIL_HOST_PASSWORD = '8n|sw?!tJB'
DEFAULT_FROM_EMAIL = 'info@torypto.com'  # Gönderen e-posta adresi

# WooCommerce Settings
WOOCOMMERCE_URL = os.getenv('WOOCOMMERCE_URL', 'https://torypto.com')
WOOCOMMERCE_CONSUMER_KEY = os.getenv('WOOCOMMERCE_CONSUMER_KEY', 'ck_1e2857952369d100f82c8e03a3d46267630155d8')
WOOCOMMERCE_CONSUMER_SECRET = os.getenv('WOOCOMMERCE_CONSUMER_SECRET', 'cs_64f9c3a91ad71d59e638d28f02c6e7a5b0195506')
PREMIUM_PRODUCT_ID = int(os.getenv('PREMIUM_PRODUCT_ID', '62'))

# WooCommerce Page IDs
WOOCOMMERCE_CART_PAGE_ID = 8
WOOCOMMERCE_CHECKOUT_PAGE_ID = 9
WOOCOMMERCE_MYACCOUNT_PAGE_ID = 10
WOOCOMMERCE_THANKYOU_PAGE_ID = 11  # Teşekkürler sayfası ID'si

# WooCommerce Endpoints
WOOCOMMERCE_ORDER_PAY_ENDPOINT = 'order-pay'
WOOCOMMERCE_ORDER_RECEIVED_ENDPOINT = 'tesekkurler'
WOOCOMMERCE_ADD_PAYMENT_METHOD_ENDPOINT = 'odeme-ekle'

# WooCommerce Webhook Settings
WOOCOMMERCE_WEBHOOK_SECRET = os.getenv('WOOCOMMERCE_WEBHOOK_SECRET', 'torypto_webhook_2024_secure_key_!@#')
