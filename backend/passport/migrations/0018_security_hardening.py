import hashlib
from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone
import uuid


def hash_existing_tokens(apps, schema_editor):
    AuthToken = apps.get_model('passport', 'AuthToken')
    for token in AuthToken.objects.all().iterator():
        raw_token = token.token or ''
        token.token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        token.expires_at = (token.created_at or timezone.now()) + timedelta(hours=12)
        token.save(update_fields=['token_hash', 'expires_at'])


def invalidate_legacy_signatures(apps, schema_editor):
    DigitalSignature = apps.get_model('passport', 'DigitalSignature')
    for signature in DigitalSignature.objects.all().iterator():
        signature.verification_code = uuid.uuid4()
        signature.is_valid = False
        signature.save(update_fields=['verification_code', 'is_valid'])


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0017_reconcile_application_appointment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='authtoken',
            name='token_hash',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='authtoken',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authtoken',
            name='last_used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authtoken',
            name='revoked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(hash_existing_tokens, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='authtoken',
            name='token',
        ),
        migrations.AlterField(
            model_name='authtoken',
            name='token_hash',
            field=models.CharField(db_index=True, max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='authtoken',
            name='expires_at',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='digitalsignature',
            name='signature_hash',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='digitalsignature',
            name='algorithm',
            field=models.CharField(default='RSA-PSS-SHA256', max_length=50),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='key_id',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='payload_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='revoked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='verification_code',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(invalidate_legacy_signatures, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='digitalsignature',
            name='verification_code',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key_hash', models.CharField(max_length=64, unique=True)),
                ('scope', models.CharField(choices=[('account', 'Account'), ('ip', 'IP')], max_length=20)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('window_started_at', models.DateTimeField(default=timezone.now)),
                ('last_failed_at', models.DateTimeField(blank=True, null=True)),
                ('locked_until', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
