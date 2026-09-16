from .settings import *  # noqa: F403


# Tests must never connect to or modify the configured application database.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Build this app's tables directly from the current models. This also avoids
# running the production-only PostgreSQL constraint migration under SQLite.
MIGRATION_MODULES = {'passport': None}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
MALWARE_SCAN_ENABLED = False

# Uploaded test documents live only in memory. This guarantees tests cannot
# read from, overwrite, or delete the application's real media files.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.InMemoryStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
