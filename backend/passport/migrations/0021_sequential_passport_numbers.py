from django.db import migrations, models


def backfill_passport_numbers(apps, schema_editor):
    Application = apps.get_model('passport', 'Application')
    PassportNumberSequence = apps.get_model('passport', 'PassportNumberSequence')

    issued_applications = Application.objects.filter(
        status__in=['Approved', 'Completed'],
        digital_signature__is_valid=True,
        queue_token__queue_status='Completed',
    ).order_by('application_id')

    last_value = 0
    for last_value, application in enumerate(issued_applications.iterator(), start=1):
        application.passport_number = f'NP{last_value:07d}'
        application.save(update_fields=['passport_number'])

    PassportNumberSequence.objects.update_or_create(
        sequence_id=1,
        defaults={'last_value': last_value},
    )


def clear_passport_numbers(apps, schema_editor):
    Application = apps.get_model('passport', 'Application')
    PassportNumberSequence = apps.get_model('passport', 'PassportNumberSequence')
    Application.objects.update(passport_number=None)
    PassportNumberSequence.objects.filter(sequence_id=1).update(last_value=0)


class Migration(migrations.Migration):
    dependencies = [
        ('passport', '0020_application_tracking_reference'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='passport_number',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Sequential number assigned only when passport processing completes.',
                max_length=9,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='credential_schema',
            field=models.CharField(
                default='np-passport-credential-v1',
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name='PassportNumberSequence',
            fields=[
                (
                    'sequence_id',
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('last_value', models.PositiveBigIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Passport number sequence',
                'verbose_name_plural': 'Passport number sequence',
            },
        ),
        migrations.RunPython(
            backfill_passport_numbers,
            reverse_code=clear_passport_numbers,
        ),
    ]
