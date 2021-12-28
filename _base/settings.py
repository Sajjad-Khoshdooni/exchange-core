import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
import raven
from yekta_config import secret
from yekta_config.config import config

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secret('SECRET')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=False)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'raven.contrib.django.raven_compat',
    'rest_framework',

    'accounts',
    'ledger',
]

MIDDLEWARE = [
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE.insert(0, 'accounts.middleware.DisableCsrfCheck')

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


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'fa-IR'

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'public/'))

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SENTRY_CLIENT = 'raven.contrib.django.raven_compat.DjangoClient'
RAVEN_CONFIG = {
    'ignore_exceptions ': ['Http404', 'django.exceptions.http.Http404'],
    'dsn': secret('SENTRY_DSN', default=''),
    'release': raven.fetch_git_sha(os.path.dirname(os.pardir)),
    'environment': config('ENVIRONMENT', default='development')
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
    ],

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ('accounts.backends.AuthenticationBackend',)

KAVENEGAR_KEY = secret('KAVENEGAR_KEY')
