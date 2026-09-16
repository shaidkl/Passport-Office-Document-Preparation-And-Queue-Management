"""Authoritative workflow facts shared by API serializers and views."""

from django.db.models import Q


def build_workflow_facts(application):
    """Return the normalized state used to gate every passport workflow UI."""
    documents = list(application.get_current_documents())
    verified_documents = [
        document for document in documents
        if document.verification_status == 'Verified'
    ]
    rejected_documents = [
        document for document in documents
        if document.verification_status == 'Rejected'
    ]

    photo = next((
        document for document in documents
        if document.document_type == 'Passport Photo'
    ), None)
    has_identity = any(
        any(label in (document.document_type or '').casefold()
            for label in ('citizenship', 'national id', 'nid'))
        for document in documents
    )
    has_verified_identity = any(
        document.verification_status == 'Verified'
        and any(label in (document.document_type or '').casefold()
                for label in ('citizenship', 'national id', 'nid'))
        for document in documents
    )

    verified_payment = application.payments.filter(
        Q(status='VERIFIED') | Q(payment_status='Completed')
    ).order_by('-payment_id').first()
    signature = getattr(application, 'digital_signature', None)
    signature_is_valid = bool(signature and signature.is_valid)
    token = getattr(application, 'queue_token', None)

    documents_complete = bool(
        documents
        and photo
        and has_identity
        and len(verified_documents) == len(documents)
    )
    queue_complete = bool(token and token.queue_status == 'Completed')
    can_download = bool(
        application.status in {'Approved', 'Completed'}
        and application.passport_number
        and verified_payment
        and application.biometric_status == 'Verified'
        and documents_complete
        and signature_is_valid
        and queue_complete
    )

    queue_token_info = None
    if token and signature_is_valid:
        queue_token_info = {
            'token_id': token.token_id,
            'token_number': token.token_number,
            'queue_status': token.queue_status,
            'token_date': str(token.token_date) if token.token_date else None,
            'time_slot': str(token.time_slot) if token.time_slot else None,
            'called_time': str(token.called_time) if token.called_time else None,
        }

    return {
        'documents': documents,
        'verified_documents': verified_documents,
        'rejected_documents': rejected_documents,
        'photo': photo,
        'photo_verified': bool(photo and photo.verification_status == 'Verified'),
        'photo_rejected': bool(photo and photo.verification_status == 'Rejected'),
        'has_identity': has_identity,
        'has_verified_identity': has_verified_identity,
        'documents_complete': documents_complete,
        'verified_payment': verified_payment,
        'payment_verified': bool(verified_payment),
        'signature': signature,
        'signature_is_valid': signature_is_valid,
        'queue_token': token,
        'queue_token_info': queue_token_info,
        'queue_complete': queue_complete,
        'can_download': can_download,
    }
