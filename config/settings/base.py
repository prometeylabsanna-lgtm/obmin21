from pathlib import Path

from decouple import Csv, config
from django.templatetags.static import static

from src.core.colors import UNFOLD_BASE, UNFOLD_PRIMARY

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'tinymce',
    'src.core.apps.CoreConfig',
    'src.network',
    'src.rates',
    'src.leads',
    'src.content',
    'src.blog',
    'src.reviews',
    'src.bot',
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
    'src.network.middleware.CityMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'libraries': {
                'content_format': 'src.core.templatetags.content_format',
            },
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'src.core.context_processors.site_chrome',
                'src.core.context_processors.page_theme',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

UNFOLD = {
    'SITE_TITLE': 'Обмін21',
    'SITE_HEADER': 'Обмін21',
    'SITE_URL': '/',
    'SITE_LOGO': {
        'light': lambda request: static('images/logo.png'),
        'dark': lambda request: static('images/logo-footer.png'),
    },
    'SITE_FAVICONS': [
        {
            'rel': 'icon',
            'href': lambda request: static('images/favicon.ico'),
            'sizes': 'any',
        },
        {
            'rel': 'icon',
            'type': 'image/png',
            'sizes': '32x32',
            'href': lambda request: static('images/favicon-32x32.png'),
        },
        {
            'rel': 'icon',
            'type': 'image/png',
            'sizes': '48x48',
            'href': lambda request: static('images/favicon-48x48.png'),
        },
        {
            'rel': 'apple-touch-icon',
            'sizes': '180x180',
            'href': lambda request: static('images/apple-touch-icon.png'),
        },
    ],
    'SHOW_HISTORY': True,
    'STYLES': [
        lambda request: static('css/admin/site_content.css'),
    ],
    'SCRIPTS': [
        lambda request: static('js/admin/cms_image_preview.js'),
    ],
    'SIDEBAR': {
        'show_search': True,
        'command_search': True,
        'show_all_applications': False,
        'navigation': [],
    },
    'LOGIN': {
        'redirect_after': '/admin/',
    },
    'COLORS': {
        'primary': UNFOLD_PRIMARY,
        'base': UNFOLD_BASE,
        'font': {
            'subtle-light': 'var(--color-base-500)',
            'subtle-dark': 'var(--color-base-400)',
            'default-light': 'var(--color-base-800)',
            'default-dark': 'var(--color-base-50)',
            'important-light': 'var(--color-base-900)',
            'important-dark': '#ffffff',
        },
    },
}

TINYMCE_DEFAULT_CONFIG = {
    'height': 360,
    'menubar': False,
    'plugins': 'link lists',
    'toolbar': 'undo redo | bold italic underline | bullist numlist | link',
    'content_css': False,
    'skin': 'oxide',
    'promotion': False,
    'branding': False,
    'forced_root_block': 'p',
    'newline_behavior': 'block',
}

CITY_COOKIE_NAME = 'obmin21_city'
CITY_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
RATE_HOLD_MINUTES = config('RATE_HOLD_MINUTES', default=30, cast=int)

EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@obmin21.local')

TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default='')
TELEGRAM_WEBHOOK_SECRET = config('TELEGRAM_WEBHOOK_SECRET', default='')
PUBLIC_BASE_URL = config('PUBLIC_BASE_URL', default='')
TELEGRAM_WEBHOOK_URL = config('TELEGRAM_WEBHOOK_URL', default='')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'src': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'src.bot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
