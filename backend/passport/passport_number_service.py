from django.db import transaction

from .models import Application, PassportNumberSequence


PASSPORT_NUMBER_PREFIX = 'NP'
PASSPORT_NUMBER_DIGITS = 7
PASSPORT_NUMBER_LIMIT = (10 ** PASSPORT_NUMBER_DIGITS) - 1


def format_passport_number(serial):
    value = int(serial)
    if value < 1 or value > PASSPORT_NUMBER_LIMIT:
        raise ValueError('The passport number sequence is outside the supported range.')
    return f'{PASSPORT_NUMBER_PREFIX}{value:0{PASSPORT_NUMBER_DIGITS}d}'


@transaction.atomic
def assign_passport_number(application):
    """Assign the next number without consuming it when the transaction rolls back."""
    locked_application = Application.objects.select_for_update().get(
        application_id=application.application_id
    )
    if locked_application.passport_number:
        application.passport_number = locked_application.passport_number
        return locked_application.passport_number

    # Production migrations create this singleton before any allocation. The
    # fallback also supports migration-free test databases.
    PassportNumberSequence.objects.get_or_create(
        sequence_id=1,
        defaults={'last_value': 0},
    )
    sequence = PassportNumberSequence.objects.select_for_update().get(sequence_id=1)

    serial = sequence.last_value + 1
    number = format_passport_number(serial)
    while Application.objects.filter(passport_number=number).exists():
        serial += 1
        number = format_passport_number(serial)

    locked_application.passport_number = number
    locked_application.save(update_fields=['passport_number', 'last_updated'])
    sequence.last_value = serial
    sequence.save(update_fields=['last_value', 'updated_at'])

    application.passport_number = number
    return number
