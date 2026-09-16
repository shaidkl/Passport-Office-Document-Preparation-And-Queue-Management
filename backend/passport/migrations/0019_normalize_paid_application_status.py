from django.db import migrations
from django.db.models import Q


def mark_paid_unsigned_applications_pending(apps, schema_editor):
    Application = apps.get_model('passport', 'Application')
    paid_application_ids = (
        Application.objects.filter(
            Q(payments__status='VERIFIED') | Q(payments__payment_status='Completed'),
            status__in=['Approved', 'Under Review'],
        )
        .exclude(digital_signature__is_valid=True)
        .values_list('application_id', flat=True)
        .distinct()
    )
    Application.objects.filter(application_id__in=paid_application_ids).update(status='Pending')


class Migration(migrations.Migration):
    dependencies = [
        ('passport', '0018_security_hardening'),
    ]

    operations = [
        migrations.RunPython(
            mark_paid_unsigned_applications_pending,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
