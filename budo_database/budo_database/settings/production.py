from .base import *
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production.')

DEBUG = False

# Get the application URL from environment variable
APP_URL = os.environ.get('APP_URL')
if not APP_URL:
    raise ImproperlyConfigured('APP_URL must be set in production.')

ALLOWED_HOSTS = [
    APP_URL,
]

CSRF_TRUSTED_ORIGINS = [
    f'https://{APP_URL}',
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
    raise ImproperlyConfigured('DATABASE_URL must be set in production.')

REDIS_URL = os.environ.get('REDIS_URL')
if not REDIS_URL:
    raise ImproperlyConfigured('REDIS_URL must be set in production.')
parsed_redis_url = urlparse(REDIS_URL)
if (
    parsed_redis_url.scheme not in {'redis', 'rediss'}
    or not parsed_redis_url.hostname
):
    raise ImproperlyConfigured(
        'REDIS_URL must be a valid redis:// or rediss:// URL.'
    )
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    },
}

S3_REQUIRED_ENVIRONMENT_VARIABLES = (
    "S3_BUCKET_NAME",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_REGION_NAME",
    "S3_ENDPOINT_URL",
)
missing_s3_variables = [
    name for name in S3_REQUIRED_ENVIRONMENT_VARIABLES
    if not os.environ.get(name)
]
if missing_s3_variables:
    raise ImproperlyConfigured(
        "Missing required S3 environment variables: "
        + ", ".join(missing_s3_variables)
    )

S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", "virtual")
if S3_ADDRESSING_STYLE not in {"virtual", "path"}:
    raise ImproperlyConfigured(
        "S3_ADDRESSING_STYLE must be either 'virtual' or 'path'."
    )

# Private user media lives in Railway's S3-compatible bucket. Static assets
# remain local to the deployment and are served by WhiteNoise.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["S3_BUCKET_NAME"],
            "access_key": os.environ["S3_ACCESS_KEY_ID"],
            "secret_key": os.environ["S3_SECRET_ACCESS_KEY"],
            "endpoint_url": os.environ["S3_ENDPOINT_URL"],
            "region_name": os.environ["S3_REGION_NAME"],
            "addressing_style": S3_ADDRESSING_STYLE,
            "signature_version": "s3v4",
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": 6 * 60 * 60,
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
SECURE_SSL_HOST = APP_URL
