"""Continuously remove expired citizen email OTP state from the database."""

import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from passport.email_verification_service import (
    OTP_STATE_PREFIX,
    purge_expired_email_otp_states,
)
from passport.models import LoginAttempt


class Command(BaseCommand):
    help = 'Delete expired citizen email OTP state rows from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run one cleanup pass and exit.',
        )
        parser.add_argument(
            '--idle-interval',
            type=float,
            default=max(1, settings.EMAIL_VERIFICATION_OTP_CLEANUP_INTERVAL_SECONDS),
            help='Seconds to wait when no OTP state exists.',
        )

    def handle(self, *args, **options):
        run_once = options['once']
        idle_interval = max(0.25, options['idle_interval'])

        while True:
            deleted = purge_expired_email_otp_states()
            if deleted and options['verbosity']:
                self.stdout.write(f'Deleted {deleted} expired email OTP state row(s).')
            if run_once:
                return

            next_expiry = LoginAttempt.objects.filter(
                key_hash__startswith=OTP_STATE_PREFIX,
                locked_until__isnull=False,
            ).order_by('locked_until').values_list('locked_until', flat=True).first()
            delay = idle_interval
            if next_expiry:
                delay = max(0.05, (next_expiry - timezone.now()).total_seconds())
            time.sleep(delay)
