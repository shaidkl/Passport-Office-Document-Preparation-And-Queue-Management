from .integration_test_settings import *  # noqa: F403


DEBUG = False
SECRET_KEY = 'deploy-check-only-' + ('x' * 64)
ALLOWED_HOSTS = ['passport.example.invalid']
CSRF_TRUSTED_ORIGINS = ['https://passport.example.invalid']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
AUTH_TOKEN_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
PERSONNEL_MFA_REQUIRED = True
MALWARE_SCAN_ENABLED = True
DEFAULT_FROM_EMAIL = 'no-reply@passport.example.invalid'
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': {
            'host': 'smtp.example.invalid',
            'port': 587,
            'username': 'deploy-check-user',
            'password': 'deploy-check-placeholder',
            'use_tls': True,
            'timeout': 20,
        },
    },
}
