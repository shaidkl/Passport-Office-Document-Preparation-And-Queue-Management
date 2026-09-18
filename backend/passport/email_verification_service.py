"""Secure, SMTP-only email OTP verification for citizen accounts."""

import hashlib
import hmac
import logging
import re
from datetime import timedelta
from html import escape

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import LoginAttempt


logger = logging.getLogger(__name__)
OTP_STATE_SALT = 'passport.citizen-email-otp-state.v1'
OTP_VALUE_SALT = 'passport.citizen-email-otp-value.v1'
OTP_STATE_PREFIX = 'otp:'


class EmailVerificationDeliveryError(Exception):
    """Raised when a real SMTP verification message cannot be delivered."""


class InvalidEmailVerificationOtp(Exception):
    """Raised when an email verification OTP is malformed or incorrect."""


class ExpiredEmailVerificationOtp(Exception):
    """Raised when an email verification OTP exceeds its configured lifetime."""


def _keyed_digest(label, value):
    message = f'{label}:{value}'.encode('utf-8')
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        message,
        hashlib.sha256,
    ).hexdigest()


def _otp_state_key(applicant):
    identity = f'{applicant.applicant_id}:{applicant.email.strip().lower()}'
    return f'{OTP_STATE_PREFIX}{_keyed_digest(OTP_STATE_SALT, identity)[:60]}'


def purge_expired_email_otp_states(now=None):
    """Physically remove expired email OTP state rows from the database."""
    deleted, _ = LoginAttempt.objects.filter(
        key_hash__startswith=OTP_STATE_PREFIX,
        locked_until__lte=now or timezone.now(),
    ).delete()
    return deleted


def _derive_otp(applicant, generation, issued_at):
    identity = (
        f'{applicant.applicant_id}:{applicant.email.strip().lower()}:'
        f'{generation}:{issued_at.isoformat()}'
    )
    digest = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        f'{OTP_VALUE_SALT}:{identity}'.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    return f'{int.from_bytes(digest[:8], "big") % 1_000_000:06d}'


def _issue_email_verification_otp(applicant):
    """Create a new OTP state without storing the six-digit code itself."""
    purge_expired_email_otp_states()
    now = timezone.now()
    expires_at = now + timedelta(
        seconds=max(60, settings.EMAIL_VERIFICATION_TTL_SECONDS),
    )
    with transaction.atomic():
        state, created = LoginAttempt.objects.select_for_update().get_or_create(
            key_hash=_otp_state_key(applicant),
            defaults={
                'scope': 'account',
                'attempts': 1,
                'window_started_at': now,
                'locked_until': expires_at,
            },
        )
        if not created:
            state.attempts = (state.attempts % 2_147_483_646) + 1
            state.window_started_at = now
            state.last_failed_at = None
            state.locked_until = expires_at
            state.save(update_fields=[
                'attempts', 'window_started_at', 'last_failed_at', 'locked_until',
            ])
        return _derive_otp(applicant, state.attempts, state.window_started_at)


def verify_registration_email_otp(applicant, raw_otp):
    """Validate and consume the current email OTP for an applicant."""
    purge_expired_email_otp_states()
    otp = str(raw_otp or '').strip()
    if not re.fullmatch(r'\d{6}', otp):
        raise InvalidEmailVerificationOtp

    state = LoginAttempt.objects.select_for_update().filter(
        key_hash=_otp_state_key(applicant),
    ).first()
    if not state:
        raise InvalidEmailVerificationOtp
    if not state.locked_until or state.locked_until <= timezone.now():
        state.delete()
        raise ExpiredEmailVerificationOtp

    expected = _derive_otp(applicant, state.attempts, state.window_started_at)
    if not hmac.compare_digest(expected, otp):
        raise InvalidEmailVerificationOtp
    state.delete()


def _smtp_sender():
    mailer = settings.MAILERS.get('default', {})
    backend = mailer.get('BACKEND', '')
    options = mailer.get('OPTIONS', {})
    if backend != 'django.core.mail.backends.smtp.EmailBackend':
        raise EmailVerificationDeliveryError(
            'Real email delivery is not configured. Configure the SMTP environment variables.'
        )
    if not all(options.get(key) for key in ('host', 'username', 'password')):
        raise EmailVerificationDeliveryError(
            'Real email delivery is not configured. Configure the SMTP environment variables.'
        )
    sender = str(settings.DEFAULT_FROM_EMAIL or '').strip()
    if not sender or '@' not in sender:
        raise EmailVerificationDeliveryError(
            'The verification email sender address is not configured.'
        )
    return sender


def send_registration_verification_email(applicant):
    """Send one real SMTP message without returning or logging its OTP."""
    sender = _smtp_sender()
    otp = _issue_email_verification_otp(applicant)
    ttl_minutes = max(1, settings.EMAIL_VERIFICATION_TTL_SECONDS // 60)
    subject = 'Your Nepal e-Passport verification code'
    text_body = (
        f'Hello {applicant.full_name},\n\n'
        f'Your six-digit email verification code is: {otp}\n\n'
        f'This code expires in {ttl_minutes} minutes and can be used only once.\n'
        'If you did not create this account, ignore this email.'
    )
    html_body = (
        f'<p>Hello {escape(applicant.full_name)},</p>'
        '<p>Your six-digit email verification code is:</p>'
        f'<p style="font-size:28px;font-weight:700;letter-spacing:8px">{otp}</p>'
        f'<p>This code expires in {ttl_minutes} minutes and can be used only once.</p>'
        '<p>If you did not create this account, ignore this email.</p>'
    )

    try:
        sent_count = send_mail(
            subject,
            text_body,
            sender,
            [applicant.email],
            fail_silently=False,
            html_message=html_body,
        )
    except Exception as error:
        logger.exception(
            'SMTP email verification delivery failed for applicant #%s.',
            applicant.applicant_id,
        )
        raise EmailVerificationDeliveryError(
            'The verification email could not be sent. Please try again.'
        ) from error
    if sent_count != 1:
        raise EmailVerificationDeliveryError(
            'The verification email could not be sent. Please try again.'
        )
