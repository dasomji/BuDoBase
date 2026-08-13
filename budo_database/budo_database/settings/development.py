from .base import *
import dj_database_url
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-nzf&ei1yhum+vx!(lsdiode6qbmdxt7idos2m#1nbq*cd+wyy5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'coolify.tailf5ea68.ts.net',
]
# Lizardtail terminates HTTPS and forwards the original host/protocol. Trust
# those proxy headers in development so Django's same-origin CSRF check works
# for whichever HTTPS port Lizardtail allocates.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = [
    'https://coolify.tailf5ea68.ts.net',
]

# Database
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=500,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
