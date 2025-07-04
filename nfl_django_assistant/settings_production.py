"""
Production Django settings for nfl_django_assistant project.
Secure and hardened configuration for production deployment.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY SETTINGS - PRODUCTION HARDENED
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# This MUST be set as an environment variable in production
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set in production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Production allowed hosts - MUST be configured properly
ALLOWED_HOSTS = []
if os.getenv('ALLOWED_HOSTS'):
    ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS').split(',') if host.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS environment variable must be set in production")

# ==============================================================================
# SECURITY HEADERS AND HTTPS SETTINGS
# ==============================================================================

# Force HTTPS in production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Session security
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Referrer policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'nfl_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files in production
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nfl_django_assistant.urls'

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

WSGI_APPLICATION = 'nfl_django_assistant.wsgi.application'

# ==============================================================================
# DATABASE - SECURE CONFIGURATION
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'application_name': 'nfl_django_assistant_prod',
            'sslmode': 'require',  # Require SSL in production
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# Validate database configuration
required_db_vars = ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
for var in required_db_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable must be set in production")

# ==============================================================================
# PASSWORD VALIDATION - ENHANCED
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Stronger minimum length
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC AND MEDIA FILES CONFIGURATION
# ==============================================================================

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files configuration  
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Storage backend selection based on environment
USE_S3_STORAGE = os.getenv('USE_S3_STORAGE', 'False').lower() == 'true'

if USE_S3_STORAGE:
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Static files locations on S3
    STATICFILES_LOCATION = 'static'
    STATICFILES_STORAGE = 'nfl_django_assistant.storage_backends.StaticStorage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATICFILES_LOCATION}/' if AWS_S3_CUSTOM_DOMAIN else f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{STATICFILES_LOCATION}/'
    
    # Media files locations on S3
    MEDIAFILES_LOCATION = 'media'
    DEFAULT_FILE_STORAGE = 'nfl_django_assistant.storage_backends.MediaStorage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/' if AWS_S3_CUSTOM_DOMAIN else f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{MEDIAFILES_LOCATION}/'
    
    # Add S3 to installed apps
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS.append('storages')
        
else:
    # Local/WhiteNoise configuration for non-S3 deployments
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    
    # Ensure WhiteNoise is in middleware
    if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
        # Insert after SecurityMiddleware
        security_index = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
        MIDDLEWARE.insert(security_index + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Static files finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Additional static file directories
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# ==============================================================================
# CORS CONFIGURATION - RESTRICTED FOR PRODUCTION
# ==============================================================================

CORS_ALLOW_ALL_ORIGINS = False  # Never allow all origins in production

# Only allow specific origins in production
CORS_ALLOWED_ORIGINS = []
if os.getenv('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS').split(',') 
        if origin.strip()
    ]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Restrict CORS methods
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
]

# ==============================================================================
# NFL ASSISTANT SPECIFIC SETTINGS - SECURE
# ==============================================================================

NFL_MAX_RANKINGS = int(os.getenv('NFL_MAX_RANKINGS', 50))
NFL_CACHE_DURATION = int(os.getenv('NFL_CACHE_DURATION', 21600))  # 6 hours

# API Keys and sensitive settings (from environment)
ESPN_API_KEY = os.getenv('ESPN_API_KEY')
NFL_API_KEY = os.getenv('NFL_API_KEY')
SLEEPER_API_KEY = os.getenv('SLEEPER_API_KEY')

# Rate limiting settings
API_RATE_LIMIT_PER_MINUTE = int(os.getenv('API_RATE_LIMIT_PER_MINUTE', 60))
API_RATE_LIMIT_PER_HOUR = int(os.getenv('API_RATE_LIMIT_PER_HOUR', 1000))

# ==============================================================================
# LOGGING CONFIGURATION - PRODUCTION
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "{levelname}", "time": "{asctime}", "module": "{module}", "message": "{message}"}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/nfl_assistant/django.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/nfl_assistant/django_errors.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'WARNING',  # Only warnings and errors in production console
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'nfl_api': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',  # Only log slow queries and errors
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'console'],
    },
}

# ==============================================================================
# CACHING - PRODUCTION REDIS CONFIGURATION
# ==============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'ssl_cert_reqs': None,
            },
        },
        'KEY_PREFIX': 'nfl_assistant',
        'TIMEOUT': 3600,  # 1 hour default timeout
    }
}

# ==============================================================================
# EMAIL CONFIGURATION - PRODUCTION
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'nfl-assistant@yourdomain.com')

# ==============================================================================
# ADMIN SECURITY
# ==============================================================================

# Secure admin URL (should be changed from default /admin/)
ADMIN_URL = os.getenv('ADMIN_URL', 'secure-admin-panel/')

# ==============================================================================
# DEFAULT FIELD SETTINGS
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# MONITORING AND HEALTH CHECKS
# ==============================================================================

# Health check endpoint settings
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_URL = os.getenv('HEALTH_CHECK_URL', '/health/')

# Monitoring settings
MONITORING_ENABLED = True
SENTRY_DSN = os.getenv('SENTRY_DSN')  # Optional error tracking

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), sentry_logging],
        traces_sample_rate=0.1,
        send_default_pii=False
    )

# ==============================================================================
# PRODUCTION VALIDATION
# ==============================================================================

# Validate required environment variables
REQUIRED_ENV_VARS = [
    'SECRET_KEY',
    'ALLOWED_HOSTS',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Required environment variables not set: {', '.join(missing_vars)}")

print("✅ Production settings loaded successfully with enhanced security")
print(f"✅ Allowed hosts: {ALLOWED_HOSTS}")
print(f"✅ Debug mode: {DEBUG}")
print(f"✅ SSL redirect: {SECURE_SSL_REDIRECT}")
print(f"✅ Secure cookies: {SESSION_COOKIE_SECURE}")