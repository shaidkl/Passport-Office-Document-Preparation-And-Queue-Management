import hashlib
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import LoginAttempt


def _key_hash(scope, value):
    material = f"{settings.SECRET_KEY}|login|{scope}|{value.strip().lower()}"
    return hashlib.sha256(material.encode('utf-8')).hexdigest()


def _client_ip(request):
    # REMOTE_ADDR is used unless the deployment explicitly normalizes proxy
    # headers before Django. This prevents clients spoofing X-Forwarded-For.
    return request.META.get('REMOTE_ADDR') or 'unknown'


def _keys(request, identifier):
    return [
        ('account', _key_hash('account', identifier)),
        ('ip', _key_hash('ip', _client_ip(request))),
    ]


def lockout_seconds(request, identifier):
    now = timezone.now()
    remaining = 0
    for _, key_hash in _keys(request, identifier):
        attempt = LoginAttempt.objects.filter(key_hash=key_hash).first()
        if attempt and attempt.locked_until and attempt.locked_until > now:
            remaining = max(remaining, int((attempt.locked_until - now).total_seconds()) + 1)
    return remaining


def record_login_failure(request, identifier):
    now = timezone.now()
    window = timedelta(minutes=max(1, settings.LOGIN_ATTEMPT_WINDOW_MINUTES))
    lock_duration = timedelta(minutes=max(1, settings.LOGIN_LOCKOUT_MINUTES))
    max_attempts = max(1, settings.LOGIN_MAX_ATTEMPTS)

    for scope, key_hash in _keys(request, identifier):
        with transaction.atomic():
            attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(
                key_hash=key_hash,
                defaults={'scope': scope, 'window_started_at': now},
            )
            if now - attempt.window_started_at >= window:
                attempt.attempts = 0
                attempt.window_started_at = now
                attempt.locked_until = None
            attempt.attempts += 1
            attempt.last_failed_at = now
            if attempt.attempts >= max_attempts:
                attempt.locked_until = now + lock_duration
            attempt.save()


def clear_login_failures(request, identifier):
    # A successful login clears that account's failures. The IP counter is
    # retained for the current window so valid credentials cannot be used to
    # bypass address-level credential-stuffing protection.
    account_hash = _key_hash('account', identifier)
    LoginAttempt.objects.filter(key_hash=account_hash).delete()
