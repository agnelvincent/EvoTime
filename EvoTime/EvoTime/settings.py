from pathlib import Path
from decouple import config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = ["www.timeevo.life", "timeevo.life", "localhost", "127.0.0.1" ,]

AUTH_USER_MODEL = 'user_home.CustomUser'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB limit   


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',

    'admin_home',
    'user_home',
    'Products',
    'Cart',
    'Wishlist',

    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'corsheaders'
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [ 
    'django.contrib.auth.backends.ModelBackend', 
    'allauth.account.auth_backends.AuthenticationBackend'
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID'),
            'secret': config('GOOGLE_CLIENT_SECRET'),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}


CSRF_TRUSTED_ORIGINS = ["https://timeevo.life"]

CORS_ALLOWED_ORIGINS = [
    "https://www.timeevo.life",
    "http://www.timeevo.life",  
    "http://localhost:8000",  
    "http://127.0.0.1:8000"  
]


# Allauth configuration
ACCOUNT_LOGIN_METHODS = {'email'} 
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  
ACCOUNT_SIGNUP_FIELDS = ['email*']
ACCOUNT_EMAIL_VERIFICATION = "mandatory" 

LOGIN_URL = '/register'
LOGOUT_URL = '/logout'
LOGIN_REDIRECT_URL = "/home" 
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
SOCIALACCOUNT_LOGIN_ON_GET = True



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware'
]

ROOT_URLCONF = 'EvoTime.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user_home.context_processors.get_cart_item_count',
                'user_home.context_processors.razorpay_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'EvoTime.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DATABASE_NAME'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST', default='localhost'),
        'PORT': config('DATABASE_PORT', cast=int, default=5432),
    }
}

# Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT')
EMAIL_USE_TLS = config('EMAIL_USE_TLS')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and Media files

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

MEDIA_URL = '/media/'
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
