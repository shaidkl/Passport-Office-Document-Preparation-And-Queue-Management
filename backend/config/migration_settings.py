"""Database-owner settings used only by ``manage.py migrate``.

The web process keeps its restricted DB_USER account. Schema migrations may
optionally use a separate owner account supplied through ignored environment
variables, which PostgreSQL requires for ALTER TABLE operations.
"""

import os
import getpass
import sys

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


MIGRATION_DATABASE_USER = os.environ.get('DB_MIGRATION_USER', '').strip()
MIGRATION_DATABASE_PASSWORD = os.environ.get('DB_MIGRATION_PASSWORD', '')

if MIGRATION_DATABASE_USER:
    if not MIGRATION_DATABASE_PASSWORD:
        if sys.stdin.isatty():
            MIGRATION_DATABASE_PASSWORD = getpass.getpass(
                f'PostgreSQL password for migration role {MIGRATION_DATABASE_USER}: '
            )
        if not MIGRATION_DATABASE_PASSWORD:
            raise ImproperlyConfigured(
                'A PostgreSQL table-owner password is required for migrations. '
                'Run this command in an interactive terminal or set '
                'DB_MIGRATION_PASSWORD in your ignored .env file.'
            )
    DATABASES['default'] = {  # noqa: F405
        **DATABASES['default'],  # noqa: F405
        'USER': MIGRATION_DATABASE_USER,
        'PASSWORD': MIGRATION_DATABASE_PASSWORD,
    }
