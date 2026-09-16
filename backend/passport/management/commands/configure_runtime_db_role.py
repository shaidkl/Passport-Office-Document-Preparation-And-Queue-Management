import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Create or rotate the restricted PostgreSQL role used by the web application.'

    def add_arguments(self, parser):
        parser.add_argument('--role', default='passport_app')

    def handle(self, *args, **options):
        password = os.environ.get('PASSPORT_RUNTIME_DB_PASSWORD', '')
        if len(password) < 24:
            raise CommandError('PASSPORT_RUNTIME_DB_PASSWORD must contain at least 24 characters.')

        role = options['role']
        if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', role):
            raise CommandError('Role names may only contain lowercase letters, digits, and underscores.')
        database = settings.DATABASES['default']['NAME']
        quoted_role = connection.ops.quote_name(role)
        quoted_database = connection.ops.quote_name(database)
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [role])
            role_exists = cursor.fetchone() is not None
            statement = f'ALTER ROLE {quoted_role} WITH LOGIN PASSWORD %s' if role_exists else f'CREATE ROLE {quoted_role} WITH LOGIN PASSWORD %s'
            cursor.execute(statement, [password])
            cursor.execute(f'GRANT CONNECT ON DATABASE {quoted_database} TO {quoted_role}')
            cursor.execute(f'GRANT USAGE ON SCHEMA public TO {quoted_role}')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted_role}')
            cursor.execute(f'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {quoted_role}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted_role}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {quoted_role}')

        self.stdout.write(self.style.SUCCESS(f'Runtime database role {role} configured.'))
