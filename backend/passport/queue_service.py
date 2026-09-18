"""Queue-token allocation shared by payment and workflow services."""

from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone

from .models import QueueToken


@transaction.atomic
def ensure_processing_queue_token(application):
    """Issue one permanent daily queue token after verified payment."""
    queue_date = timezone.localdate()

    if connection.vendor == 'postgresql':
        # Serialize daily MAX+1 allocation, including when the day has no rows.
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)',
                [0x50535000 + queue_date.toordinal()],
            )

    token = QueueToken.objects.select_for_update().filter(
        application=application
    ).first()
    if token is not None:
        signature = getattr(application, 'digital_signature', None)
        if token.queue_status == 'Skipped' and not (signature and signature.is_valid):
            current_max = QueueToken.objects.filter(
                token_date=queue_date
            ).aggregate(Max('token_number'))['token_number__max']
            token.token_number = (current_max + 1) if current_max else 101
            token.token_date = queue_date
            token.time_slot = None
            token.queue_status = 'Waiting'
            token.called_time = None
            token.staff = None
            token.save(update_fields=[
                'token_number',
                'token_date',
                'time_slot',
                'queue_status',
                'called_time',
                'staff',
            ])
        return token

    current_max = QueueToken.objects.filter(
        token_date=queue_date
    ).aggregate(Max('token_number'))['token_number__max']

    return QueueToken.objects.create(
        application=application,
        token_number=(current_max + 1) if current_max else 101,
        queue_status='Waiting',
    )
