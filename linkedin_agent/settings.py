"""
Django settings for Qrious Tech Academy  Production-Ready SaaS
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*', '.vercel.app', '.now.sh', 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app', 'https://*.now.sh', 'http://127.0.0.1:8000', 'http://localhost:8000']

#  APPS 
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # REST Framework & JWT Authentication
    'rest_framework',
    'rest_framework_simplejwt',

    # AllAuth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Local apps
    'landing',
    'accounts_app',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'linkedin_agent.auto_setup.AutoSetupMiddleware',
]

ROOT_URLCONF = 'linkedin_agent.urls'

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
                'accounts_app.context_processors.subscription_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'linkedin_agent.wsgi.application'

#  DATABASE (MySQL for Production Deployment) 
DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.mysql')
DB_NAME = os.getenv('DB_NAME', 'qrious_tech_db')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '3306')

if os.getenv('DATABASE_URL'):
    import dj_database_url
    db_config = dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=60,
        conn_health_checks=True,
    )
    if 'OPTIONS' in db_config:
        db_config['OPTIONS'].pop('ssl-mode', None)
        db_config['OPTIONS'].pop('ssl_mode', None)
        if 'aivencloud.com' in os.getenv('DATABASE_URL', '') and 'ssl' not in db_config['OPTIONS']:
            db_config['OPTIONS']['ssl'] = {'ssl_mode': 'REQUIRED'}
    DATABASES = {'default': db_config}
elif os.getenv('DB_HOST') and os.getenv('DB_NAME'):
    db_opts = {'charset': 'utf8mb4'}
    if 'aivencloud.com' in os.getenv('DB_HOST', ''):
        db_opts['ssl'] = {'ssl_mode': 'REQUIRED'}
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': db_opts,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

#  AUTH 
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

#  ALLAUTH 
ACCOUNT_LOGIN_METHODS = {'email'}                  # replaces ACCOUNT_AUTHENTICATION_METHOD
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']  # replaces EMAIL_REQUIRED + USERNAME_REQUIRED
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_HTML_FORMAT = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Qrious Tech Academy] '
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_REDIRECT_URL = '/auth/redirect/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SIGNUP_REDIRECT_URL = '/auth/redirect/'
LOGIN_REDIRECT_URL = '/auth/redirect/'
LOGIN_URL = '/auth/login/'

# Permanent 30-Day Session Persistence Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60       # 30 Days persistence
SESSION_SAVE_EVERY_REQUEST = True             # Auto-refresh session timer on activity
SESSION_EXPIRE_AT_BROWSER_CLOSE = False        # Keep logged in when browser closes & reopens
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'sessionid'              # Standard Django session cookie name

# Cookie Security & SSL Proxy Settings for Vercel
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# AllAuth Remember Me Always Active
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True

# Google OAuth
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

#  EMAIL 
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'mdsiamh77@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '').replace(' ', '')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = f'Qrious Tech Academy <{EMAIL_HOST_USER}>'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'Qrious Tech Academy <noreply@qrioussolution.com>'

#  STRIPE (Test Mode) 
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Price IDs (create these in Stripe dashboard)
STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO', 'price_pro_placeholder')
STRIPE_PRICE_BUSINESS = os.getenv('STRIPE_PRICE_BUSINESS', 'price_business_placeholder')

#  SUBSCRIPTION LIMITS 
PLAN_LIMITS = {
    'free': {
        'applications_per_month': 30,
        'linkedin_accounts': 1,
        'resumes': 1,
        'ai_cover_letters': False,
        'label': 'Free',
        'price': 0,
        'price_bdt': 0,
    },
    'pro': {
        'applications_per_month': 1000,
        'linkedin_accounts': 3,
        'resumes': 5,
        'ai_cover_letters': True,
        'label': 'Pro',
        'price': 9,
        'price_bdt': 250,
    },
    'business': {
        'applications_per_month': 99999,
        'linkedin_accounts': 10,
        'resumes': 99,
        'ai_cover_letters': True,
        'label': 'Business',
        'price': 29,
        'price_bdt': 999,
    },
}

#  INTERNATIONALIZATION 
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True
DATETIME_FORMAT = 'M d, Y, h:i A'
TIME_FORMAT = 'h:i A'

#  STATIC & MEDIA 
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

MEDIA_URL = '/media/'
# On serverless platforms like Vercel, use /tmp/media for writable uploads
if os.getenv('VERCEL') or '/var/task' in str(BASE_DIR) or not os.access(BASE_DIR, os.W_OK):
    MEDIA_ROOT = '/tmp/media'
else:
    MEDIA_ROOT = BASE_DIR / 'media'

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# LinkedIn Agent encryption key
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#  JWT AUTHENTICATION (SimpleJWT) 
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'accounts_app.api_auth.CsrfExemptSessionAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),   # 30 Days JWT Access Token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),  # 90 Days JWT Refresh Token
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer', 'JWT'),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}
