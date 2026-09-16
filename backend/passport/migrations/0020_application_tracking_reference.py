import uuid

from django.db import migrations, models


def populate_tracking_references(apps, schema_editor):
    Application = apps.get_model('passport', 'Application')
    for application in Application.objects.filter(tracking_reference__isnull=True).iterator():
        application.tracking_reference = uuid.uuid4()
        application.save(update_fields=['tracking_reference'])


class Migration(migrations.Migration):
    dependencies = [
        ('passport', '0019_normalize_paid_application_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='tracking_reference',
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(
            populate_tracking_references,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='application',
            name='tracking_reference',
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
