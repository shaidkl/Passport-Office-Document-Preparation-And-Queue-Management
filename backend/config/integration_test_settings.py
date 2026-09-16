from .settings import *  # noqa: F403


PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
MALWARE_SCAN_ENABLED = False
PERSONNEL_MFA_REQUIRED = False

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.InMemoryStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
