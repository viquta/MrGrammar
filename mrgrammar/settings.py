import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'unsafe-dev-secret-key-change-me',
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Local apps
    'accounts',
    'classrooms',
    'submissions',
    'feedback',
    'analytics',
    'nlp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mrgrammar.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mrgrammar.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'mrgrammar'),
        'USER': os.environ.get('POSTGRES_USER', 'mrgrammar'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'change-me-local-password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ──
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ── JWT ──
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
}

# ── CORS ──
# In production (nginx on port 80) the browser origin is http://localhost.
# In dev the Vite dev server runs on :5173. Both need to be allowed by default.
_default_cors = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost,http://127.0.0.1'
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CORS_ALLOWED_ORIGINS', _default_cors).split(',')
    if o.strip()
]

# ── MrGrammar Configuration (NFR-8.4: configurable without code changes) ──
MRGRAMMAR = {
    'MAX_CORRECTION_ATTEMPTS': int(os.environ.get('MAX_CORRECTION_ATTEMPTS', '2')),
    'HINT_THRESHOLD': int(os.environ.get('HINT_THRESHOLD', '1')),
    'SUPPORTED_LANGUAGES': os.environ.get('SUPPORTED_LANGUAGES', 'de').split(','),
    'LANGUAGETOOL_URL': os.environ.get('LANGUAGETOOL_URL', 'http://localhost:8010/v2'),
    'SPACY_MODEL': os.environ.get('SPACY_MODEL', 'de_core_news_md'),
    'SPACY_SENTENCE_SPLIT': os.environ.get('SPACY_SENTENCE_SPLIT', 'True').lower() in ('true', '1', 'yes'),
    'ENABLE_ADVANCED_GERMAN_CHECKS': os.environ.get('ENABLE_ADVANCED_GERMAN_CHECKS', 'False').lower() in ('true', '1', 'yes'),
    'ENABLE_LLM_EXPLANATIONS': os.environ.get('ENABLE_LLM_EXPLANATIONS', 'True').lower() in ('true', '1', 'yes'),
    'OLLAMA_BASE_URL': os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
    'OLLAMA_MODEL': os.environ.get('OLLAMA_MODEL', 'gemma4:26b'),
    'OLLAMA_TIMEOUT_SECONDS': int(os.environ.get('OLLAMA_TIMEOUT_SECONDS', '15')),
    'OLLAMA_EXPLANATION_TEMPERATURE': float(os.environ.get('OLLAMA_EXPLANATION_TEMPERATURE', '0.2')),
}
