import os
from pathlib import Path

from import_export.formats.base_formats import XLSX

from dotenv import load_dotenv

BASE_APP_DIR = Path(__file__).resolve().parent.parent
BASE_PRJ_DIR = BASE_APP_DIR.parent

dotenv_path = BASE_PRJ_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path, encoding="utf-8")

# Имя приложения в ОС - используется в путях к логам, временным файлам и т.д.
APP_SYSNAME = 'ops'

SECRET_KEY = 'asdashdbqkwuhb1li23nbl12iuhwey'

IS_PRODUCTION = os.getenv("IS_PRODUCTION", "False") == "True"

DEBUG = not IS_PRODUCTION

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "92.118.114.27", "192.168.3.143", "wicad-ops.witz.local", "92.50.148.46"]

# app: django.contrib.sites
SITE_ID = 1

APP_REDIS_CONNECTION = os.getenv("APP_REDIS_CONNECTION", "redis://localhost:6379/2")

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'modeltranslation',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'user_sessions',

    'django.contrib.messages',
    'django.contrib.staticfiles',

    'constance',
    'constance.backends.database',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_bootstrap5',
    'channels',
    'django_extensions',
    'rangefilter',
    'pybarker.contrib.modelshistory',
    'nested_admin',
    'import_export',
    'rest_framework',
    'django_filters',
    'drf_yasg',
    'corsheaders',
    'auditlog',

    # project apps
    'kernel',
    'ops',
    'catalog',
    'taskmanager',
]

MIDDLEWARE = [
    'kernel.api.middleware.ConvertFiltersToQueryParamsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'user_sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pybarker.django.middleware.threadrequest.ThreadRequestMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_APP_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "wzn_3",
        'USER': "postgres",
        'PASSWORD': "Max332628",
        'HOST': "localhost",
        'PORT': "5432",
    }
}

AUTHENTICATION_BACKENDS = [
    'ops.auth.CRMAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

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

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'CRM_API_URL': ('', 'API-точка к CRM'),
    'COMMON_COMMENT': ('', 'Комментарий к эскизам продукции'),
    'ERP_BASE_URL': ('', 'API-точка к ERP'),
    'ERP_LOGIN': ('', 'Логин ERP'),
    'ERP_PASSWORD': ('', 'Пароль ERP'),
    'TECHNICAL_REQUIREMENTS': (
        "",
        'Технические требования проектов',
    ),
    'TEMPERATURE_WITH_INSULATION': (25, 'Температура среды с изоляцией'),
    'SSB_CATALOG_PARAM_KEY': ('catalog', 'Ключ в JSON-поле Item.parameters, где лежит список записей SSB-каталога'),
    'SSB_SN_MARGIN_COEF': (1.2, 'Коэффициент запаса хода для Sn (по умолчанию 1.2)'),
    'SSB_EXTRA_MARGIN_PERCENT': (0.1, 'Дополнительный запас для типа 1 в процентах (по умолчанию 10%)'),
    "SVG_TEXT_FONT_PATH": ("Arial.ttf", "Шрифт текста в svg скетче"),
    "SKETCH_IMAGE_TEXT_FONT_PATH": ("arial.ttf", "Шрифт текста в изображении скетча"),
}

CONSTANCE_CONFIG_FIELDSETS = {
    'CRM': ('CRM_API_URL',),
    'COMMENTS': ('COMMON_COMMENT',),
    'ERP': ('ERP_BASE_URL', 'ERP_LOGIN', 'ERP_PASSWORD'),
    'Tехнические требования': ('TECHNICAL_REQUIREMENTS',),
    'TEMPERATURE_WITH_INSULATION': ('TEMPERATURE_WITH_INSULATION',),
    'SSB_SHOCK_CALC': (
        'SSB_CATALOG_PARAM_KEY',
        'SSB_SN_MARGIN_COEF',
        'SSB_EXTRA_MARGIN_PERCENT',
    ),
    "SKETCHES": ("SVG_TEXT_FONT_PATH", "SKETCH_IMAGE_TEXT_FONT_PATH"),
}

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

SESSION_ENGINE = 'user_sessions.backends.db'

SILENCED_SYSTEM_CHECKS = ['admin.E410']

# api
REST_FLEX_FIELDS = {'EXPAND_PARAM': 'expand'}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'kernel.api.authentication.LoginAPINoAuthentication',
        'kernel.api.authentication.BearerAuthentication',
        'kernel.api.authentication.ApiTokenAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'kernel.api.filter_backends.MappedOrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'kernel.api.pagination.DynamicPageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'EXCEPTION_HANDLER': 'kernel.api.exceptions.custom_exception_handler',
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    },
    'DEFAULT_FILTER_INSPECTORS': [
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
    'USE_SESSION_AUTH': False,
    'PERSIST_AUTH': True,
    'DEFAULT_AUTO_SCHEMA_CLASS': 'kernel.api.schema.AutoSchema',
    'DEFAULT_GENERATOR_CLASS': 'kernel.api.generators.SchemaGenerator',
}

# django-cors-headers
CORS_ALLOWED_ORIGINS = [
    "http://92.118.114.27",
    "http://92.118.114.27:8111",
    "http://92.50.148.46",
    "http://92.50.148.46:8111",
    "http://192.168.3.143",
    "http://192.168.3.143:8111",
    "http://localhost:3000",
    "http://wicad-ops.witz.local:8111"
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://92.118.114.27",
    "http://192.168.3.143",
    "http://192.168.3.143:8111",
    "http://92.50.148.46",
    "http://92.50.148.46:8111",
    "http://localhost:3000",
    "http://wicad-ops.witz.local:8111"
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# app: auth
AUTH_USER_MODEL = 'kernel.User'

# app: django-import-export
IMPORT_EXPORT_SKIP_ADMIN_LOG = True  # Пропускаем запись в лог админки (Ускоряет процесс импорта)
IMPORT_FORMATS = (XLSX,)  # Пока поддерживаем только xlsx-файлы


def gettext(s):
    return s


LANGUAGES = (
    ('ru', gettext('Russian')),
    ('en', gettext('English')),
)

LOCALE_PATHS = [BASE_APP_DIR / 'locale']
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Yekaterinburg'
USE_I18N = True
USE_TZ = True

if IS_PRODUCTION:
    STATIC_ROOT = f"/var/www/{APP_SYSNAME}/static"
    MEDIA_ROOT = f"/var/www/{APP_SYSNAME}/media"
else:
    STATIC_ROOT = BASE_PRJ_DIR / "var" / "static"
    MEDIA_ROOT = BASE_PRJ_DIR / "var" / "media"

STATIC_URL = "static/"
MEDIA_URL = "media/"

STATICFILES_DIRS = [BASE_APP_DIR / "static-common"]

if IS_PRODUCTION:
    LOG_PREFIX = f"/var/log/{APP_SYSNAME}"
else:
    LOG_PREFIX = BASE_PRJ_DIR / "var" / "log"

# Логирование
from .settings_logging import *  # noqa

# modelshistory
MODELSHISTORY_USER_MODEL = AUTH_USER_MODEL

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# отключаем проверку кол-ва полей формы, иначе в админке падает если много всего
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# APP_REDIS_CONNECTION = 'redis://localhost:6379/2'
#
# # Кеширование
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': APP_REDIS_CONNECTION,
#         'KEY_PREFIX': 'ops:',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#     },
# }
#
# CELERY_BROKER_URL = APP_REDIS_CONNECTION
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_IGNORE_RESULT = True
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_EVENT_SERIALIZER = 'json'
# CELERY_WORKER_CONCURRENCY = 5 if not DEBUG else 1
# CELERY_TIMEZONE = TIME_ZONE
# CELERYD_HIJACK_ROOT_LOGGER = False


ASGI_APPLICATION = 'project.asgi.application'
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [APP_REDIS_CONNECTION],
#             # попытка тюнинга групп/каналов от сообщения
#             # INFO [channels_redis.core:core:731] 1 of 3 channels over capacity in group user-3
#             'expiry': 30,  # default 60
#             'capacity': 666,  # default 100
#         },
#     },
# }

# app: bootstrap5
BOOTSTRAP5 = {
    'set_placeholder': False,
}
