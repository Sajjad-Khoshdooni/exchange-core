import os
import re
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
import raven
from decouple import Csv
from yekta_config import secret
from yekta_config.config import config

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secret('SECRET')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=False)

HOST_URL = config('HOST_URL')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'raven.contrib.django.raven_compat',
    'django_admin_listfilter_dropdown',
    'rest_framework',
    'corsheaders',
    'hijack',
    'hijack.contrib.admin',
    'django_filters',

    'financial',
    'multimedia',
    'accounts',
    'ledger',
    'tracker',
    'provider',
    'wallet',
    'collector',
    'simple_history',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hijack.middleware.HijackUserMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

MIDDLEWARE.insert(0, 'accounts.middleware.DisableCsrfCheck')
MIDDLEWARE.remove('django.middleware.csrf.CsrfViewMiddleware')

if DEBUG:
    MIDDLEWARE.remove('hijack.middleware.HijackUserMiddleware')

ROOT_URLCONF = '_base.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = '_base.wsgi.application'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='')

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv(), default='')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default='')
CORS_ALLOW_CREDENTIALS = True

KAVENEGAR_KEY = secret('KAVENEGAR_KEY')

DATABASES = {
    'default': {
        'ENGINE': config('DEFAULT_DB_ENGINE', default='django.db.backends.postgresql_psycopg2'),
        'NAME': config('DEFAULT_DB_NAME', default='core'),
        'USER': config('DEFAULT_DB_USER', default='exchange'),
        'PASSWORD': secret('DEFAULT_DB_PASSWORD'),
        'HOST': config('DEFAULT_DB_HOST', default='localhost'),
        'PORT': config('DEFAULT_DB_PORT', default=5432),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': secret('DEFAULT_CACHE_LOCATION', default='redis://127.0.0.1:6379/0'),

        'OPTIONS': {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    'token': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': secret('TOKEN_CACHE_LOCATION', default='redis://127.0.0.1:6379/0'),

        'OPTIONS': {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

PROVIDER_CACHE_LOCATION = secret('PROVIDER_CACHE_LOCATION', default='redis://127.0.0.1:6379/0')

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'fa-IR'

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'public/'))

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media/'))


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SENTRY_CLIENT = 'raven.contrib.django.raven_compat.DjangoClient'
RAVEN_CONFIG = {
    'ignore_exceptions ': ['Http404', 'django.exceptions.http.Http404', 'rest_framework.exceptions.PermissionDenied'],
    'dsn': secret('SENTRY_DSN', default=''),
    'release': raven.fetch_git_sha(os.path.dirname(os.pardir)),
    'environment': config('ENVIRONMENT', default='development')
}

REST_FRAMEWORK = {
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_PAGINATION_CLASS': None,
    'PAGE_SIZE': 20,

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
    ],

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ('accounts.backends.AuthenticationBackend',)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '[contactor] %(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'sentry': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'sentry'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# SESSION_COOKIE_DOMAIN = '.chavosh.org'
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_DOMAIN = '.raastin.com'
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True

if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.zoho.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = 'info@raastin.com'
    EMAIL_HOST_PASSWORD = ''

else:
    # start a smtp server with `python -m smtpd -n -c DebuggingServer localhost:1025`
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False

