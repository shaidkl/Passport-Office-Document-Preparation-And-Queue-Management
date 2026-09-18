import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

from django.conf import settings
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class SigningConfigurationError(RuntimeError):
    pass


def _iso_date(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


SUPPORTED_CREDENTIAL_SCHEMAS = {
    'np-passport-credential-v1',
    'np-passport-credential-v2',
}


def _canonical_payload(application, schema='np-passport-credential-v1'):
    if schema not in SUPPORTED_CREDENTIAL_SCHEMAS:
        raise ValueError('Unsupported passport credential schema.')
    verified_payment = application.payments.filter(
        status='VERIFIED'
    ).order_by('-verified_at', '-payment_id').first()
    if verified_payment is None:
        verified_payment = application.payments.filter(
            payment_status='Completed'
        ).order_by('-payment_id').first()

    documents = []
    for document in application.documents.filter(verification_status='Verified').order_by('document_id'):
        file_digest = ''
        try:
            digest = hashlib.sha256()
            with document.open_preserved_file() as source:
                for chunk in iter(lambda: source.read(64 * 1024), b''):
                    digest.update(chunk)
            file_digest = digest.hexdigest()
        except (OSError, ValueError):
            file_digest = 'unavailable'
        documents.append({
            'document_id': document.document_id,
            'type': document.document_type,
            'sha256': file_digest,
        })

    payload = {
        'schema': schema,
        'application_reference': f'NP-{application.application_id:04d}',
        'applicant_id': application.applicant_id,
        'full_name': application.applicant.full_name,
        'date_of_birth': _iso_date(application.applicant.date_of_birth),
        'nationality': application.applicant.nationality,
        'passport_category': application.passport_category,
        'service_type': application.service_type,
        'issue_date': _iso_date(application.issue_date),
        'expiry_date': _iso_date(application.expiry_date),
        'payment_reference': (
            verified_payment.payment_reference or verified_payment.transaction_id
            if verified_payment else None
        ),
        'documents': documents,
    }
    if schema == 'np-passport-credential-v2':
        payload['passport_number'] = application.passport_number
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _inline_key(value):
    return value.replace('\\n', '\n').encode('utf-8') if value else None


def _read_path(path_value):
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SigningConfigurationError('Unable to read the configured signing key file.') from exc


def _development_key_material():
    secret_dir = Path(settings.BASE_DIR) / '.secrets'
    private_path = secret_dir / 'passport_signing_private.pem'
    public_path = secret_dir / 'passport_signing_public.pem'
    if not private_path.exists():
        secret_dir.mkdir(parents=True, exist_ok=True)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        private_bytes = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        private_path.write_bytes(private_bytes)
        public_path.write_bytes(public_bytes)
        try:
            os.chmod(private_path, 0o600)
            os.chmod(public_path, 0o644)
        except OSError:
            pass
    return private_path.read_bytes(), public_path.read_bytes()


def _private_key():
    material = _inline_key(settings.PASSPORT_SIGNING_PRIVATE_KEY)
    material = material or _read_path(settings.PASSPORT_SIGNING_PRIVATE_KEY_FILE)
    if material is None and settings.DEBUG:
        material, _ = _development_key_material()
    if material is None:
        raise SigningConfigurationError('Passport signing private key is not configured.')
    try:
        return serialization.load_pem_private_key(material, password=None)
    except (TypeError, ValueError) as exc:
        raise SigningConfigurationError('Passport signing private key is invalid.') from exc


def _public_key():
    material = _inline_key(settings.PASSPORT_SIGNING_PUBLIC_KEY)
    material = material or _read_path(settings.PASSPORT_SIGNING_PUBLIC_KEY_FILE)
    if material is not None:
        try:
            return serialization.load_pem_public_key(material)
        except (TypeError, ValueError) as exc:
            raise SigningConfigurationError('Passport signing public key is invalid.') from exc
    return _private_key().public_key()


def public_key_fingerprint():
    public_der = _public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(public_der).hexdigest()


def sign_application(application):
    schema = (
        'np-passport-credential-v2'
        if application.passport_number
        else 'np-passport-credential-v1'
    )
    payload = _canonical_payload(application, schema=schema)
    signature = _private_key().sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    fingerprint = public_key_fingerprint()
    return {
        'signature': base64.b64encode(signature).decode('ascii'),
        'payload_hash': hashlib.sha256(payload).hexdigest(),
        'algorithm': 'RSA-PSS-SHA256',
        'key_id': f'{settings.PASSPORT_SIGNING_KEY_ID}:{fingerprint[:16]}',
        'credential_schema': schema,
    }


def verify_signature(digital_signature):
    if digital_signature.revoked_at is not None or not digital_signature.is_valid:
        return False
    schema = digital_signature.credential_schema or 'np-passport-credential-v1'
    try:
        payload = _canonical_payload(digital_signature.application, schema=schema)
    except ValueError:
        return False
    if not digital_signature.payload_hash:
        return False
    if not hmac.compare_digest(
        digital_signature.payload_hash,
        hashlib.sha256(payload).hexdigest(),
    ):
        return False
    try:
        signature = base64.b64decode(digital_signature.signature_hash, validate=True)
        _public_key().verify(
            signature,
            payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
