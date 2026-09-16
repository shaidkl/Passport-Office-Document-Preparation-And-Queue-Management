from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Q, Max, Sum
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import redirect
from urllib.parse import urlencode
import os
import re
import secrets
import json
import logging
from datetime import timedelta
from decimal import Decimal
from .models import AuthToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from .authentication import CustomTokenAuthentication
from .pdf_generator import generate_passport_pdf
from .digital_signature_service import (
    SigningConfigurationError,
    sign_application,
    verify_signature,
)
from .login_security import (
    clear_login_failures,
    lockout_seconds,
    record_login_failure,
)
from .upload_security import UploadSecurityError, validate_uploaded_document
from .workflow_service import build_workflow_facts
from .passport_number_service import assign_passport_number
from .throttles import PublicTrackingThrottle

from .permissions import (
    IsAdministrator,
    IsStaff,
    IsApplicant,
    IsStaffOrAdministrator
)

from .models import (
    Applicant,
    Staff,
    Administrator,
    Application,
    Document,
    DigitalSignature,
    QueueToken,
    Report,
    ActivityLog,
    Notification,
    Payment,
)

from .serializers import (
    CitizenRegistrationSerializer,
    ApplicantSerializer,
    StaffSerializer,
    AdministratorSerializer,
    ApplicationSerializer,
    DocumentSerializer,
    DigitalSignatureSerializer,
    QueueTokenSerializer,
    ReportSerializer,
    ActivityLogSerializer,
    NotificationSerializer,
    PaymentSerializer,
)


logger = logging.getLogger(__name__)


def _as_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _login_payload(user_type, user):
    if user_type == 'administrator':
        return {
            'role': 'administrator', 'user_id': user.admin_id,
            'name': user.full_name, 'username': user.username, 'email': user.email,
        }
    if user_type == 'staff':
        return {
            'role': 'staff', 'user_id': user.staff_id,
            'name': user.full_name, 'username': user.username, 'email': user.email,
            'department': user.department, 'designation': user.designation,
        }
    return {
        'role': 'citizen', 'user_id': user.applicant_id,
        'name': user.full_name, 'email': user.email,
    }


def _issue_login_response(user_type, user, remember_me=False):
    raw_token, auth_session = AuthToken.issue(user_type, user.pk)
    response = Response({
        'message': 'Login successful.',
        **_login_payload(user_type, user),
        'expires_at': auth_session.expires_at,
    }, status=status.HTTP_200_OK)
    cookie_options = {
        'key': settings.AUTH_TOKEN_COOKIE_NAME,
        'value': raw_token,
        'httponly': True,
        'secure': settings.AUTH_TOKEN_COOKIE_SECURE,
        'samesite': settings.AUTH_TOKEN_COOKIE_SAMESITE,
        'path': '/',
    }
    if remember_me:
        cookie_options['max_age'] = max(1, settings.AUTH_TOKEN_TTL_MINUTES) * 60
    response.set_cookie(**cookie_options)
    return response


def _personnel_account_is_active(user_type, user):
    if user_type == 'administrator':
        return bool(user.is_active)
    if user_type == 'staff':
        return bool(user.is_active and user.status == 'Active')
    return True


def _start_personnel_mfa(user_type, user, remember_me):
    otp = f"{secrets.randbelow(1_000_000):06d}"
    challenge = SessionStore()
    challenge.update({
        'challenge_kind': 'personnel_mfa',
        'user_type': user_type,
        'user_id': user.pk,
        'otp_hash': make_password(otp),
        'attempts': 0,
        'remember_me': bool(remember_me),
    })
    challenge.set_expiry(settings.PERSONNEL_MFA_TTL_SECONDS)
    challenge.save()
    try:
        send_mail(
            'Your Nepal e-Passport personnel verification code',
            f'Your verification code is {otp}. It expires in {settings.PERSONNEL_MFA_TTL_SECONDS // 60 or 1} minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Personnel MFA delivery failed for %s:%s', user_type, user.pk)
        Session.objects.filter(session_key=challenge.session_key).delete()
        return Response(
            {'error': 'Verification code delivery is temporarily unavailable.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({
        'message': 'A verification code was sent to your registered email address.',
        'mfa_required': True,
        'challenge_id': challenge.session_key,
        'role': 'administrator' if user_type == 'administrator' else 'staff',
        'expires_in': settings.PERSONNEL_MFA_TTL_SECONDS,
    }, status=status.HTTP_202_ACCEPTED)


def _next_daily_queue_number(queue_date):
    """Allocate the next daily queue number inside the caller's transaction."""
    if connection.vendor == 'postgresql':
        # Serialize daily MAX+1 allocation even when there is no row to lock.
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)',
                [0x50535000 + queue_date.toordinal()],
            )
    current_max = QueueToken.objects.filter(
        token_date=queue_date
    ).aggregate(Max('token_number'))['token_number__max']
    return (current_max + 1) if current_max else 101


def _ensure_processing_queue_token(application):
    """Assign the processing token only after the application is digitally signed."""
    queue_date = timezone.localdate()
    token = QueueToken.objects.select_for_update().filter(
        application=application
    ).first()

    if token is None:
        token = QueueToken.objects.create(
            application=application,
            token_number=_next_daily_queue_number(queue_date),
            queue_status='Waiting',
        )
    elif token.queue_status in {'Completed', 'Skipped'} and application.status not in {'Approved', 'Completed'}:
        # Normalize legacy/pre-workflow tokens without deleting their record.
        token.token_number = _next_daily_queue_number(queue_date)
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


def _current_document_review_is_complete(application):
    """Require a verified photo, verified identity record, and no unresolved latest upload."""
    documents = application.get_current_documents()
    has_photo = any(
        document.document_type == 'Passport Photo'
        and document.verification_status == 'Verified'
        for document in documents
    )
    has_identity = any(
        document.verification_status == 'Verified'
        and any(
            label in (document.document_type or '').casefold()
            for label in ('citizenship', 'national id', 'nid')
        )
        for document in documents
    )
    all_current_verified = bool(documents) and all(
        document.verification_status == 'Verified'
        for document in documents
    )
    return has_photo and has_identity and all_current_verified


def _sign_application_record(application):
    signed = sign_application(application)
    signature, _ = DigitalSignature.objects.update_or_create(
        application=application,
        defaults={
            'signature_hash': signed['signature'],
            'payload_hash': signed['payload_hash'],
            'signing_authority': 'Department of Passports, Government of Nepal',
            'certificate_serial': (
                f'NPL-DOP-PKI-{timezone.localdate().year}-{application.application_id:04d}'
            ),
            'algorithm': signed['algorithm'],
            'key_id': signed['key_id'],
            'credential_schema': signed['credential_schema'],
            'is_valid': True,
            'revoked_at': None,
            'signed_at': timezone.now(),
        },
    )
    return signature


# 1. APPLICANT API

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all().order_by('-applicant_id')
    serializer_class = ApplicantSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [
        IsApplicant | IsStaffOrAdministrator
    ]

    def get_permissions(self):
        if self.action in {'create', 'destroy'}:
            return [IsAdministrator()]
        if self.action in {'update', 'partial_update'}:
            return [(IsApplicant | IsAdministrator)()]
        return [(IsApplicant | IsStaffOrAdministrator)()]

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return Applicant.objects.filter(applicant_id=user_id)
        return Applicant.objects.all().order_by('-applicant_id')

    def destroy(self, request, *args, **kwargs):
        user_type = getattr(request.user, 'user_type', None)
        if user_type != 'administrator':
            return Response(
                {"error": "Only Administrators can remove applicant accounts."},
                status=status.HTTP_403_FORBIDDEN
            )
        applicant = self.get_object()
        if Application.objects.filter(applicant=applicant).exists():
            return Response(
                {
                    "error": (
                        "This citizen has passport application history and cannot be deleted. "
                        "Retain the account to preserve official records."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        user_type = getattr(self.request.user, 'user_type', None)
        instance = self.get_object()
        if user_type == 'applicant':
            protected_account_fields = {'email', 'phone', 'password'}
            changed_account_fields = [
                field for field in protected_account_fields
                if field in serializer.validated_data
                and serializer.validated_data[field] != getattr(instance, field)
            ]
            if changed_account_fields:
                raise PermissionDenied(
                    "Email, phone, and password require a dedicated secure change workflow."
                )

            identity_fields = {'full_name', 'date_of_birth', 'gender', 'nationality'}
            changed_identity_fields = [
                field for field in identity_fields
                if field in serializer.validated_data
                and serializer.validated_data[field] != getattr(instance, field)
            ]
            if changed_identity_fields and Application.objects.filter(
                applicant_id=instance.applicant_id
            ).exists():
                raise PermissionDenied(
                    "Identity details cannot be changed after a passport application has been submitted."
                )
        serializer.save()

    @action(detail=True, methods=['get'], url_path='profile-photo')
    def profile_photo(self, request, pk=None):
        """Serve the applicant's newest verified Passport Photo as their avatar."""
        applicant = self.get_object()
        photo = Document.objects.filter(
            application__applicant=applicant,
            document_type='Passport Photo',
            verification_status='Verified',
        ).exclude(file_path='').order_by('-upload_date', '-document_id').first()

        if not photo or not photo.file_path:
            return Response(
                {"error": "No verified profile photo is available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        import mimetypes
        from django.http import FileResponse

        filename = photo.file_name or os.path.basename(photo.file_path.name)
        content_type, _ = mimetypes.guess_type(filename)
        if content_type not in {'image/jpeg', 'image/png'}:
            return Response(
                {"error": "The verified profile photo has an unsupported image format."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        try:
            file_handle = photo.file_path.open('rb')
        except (FileNotFoundError, OSError):
            return Response(
                {"error": "The verified profile photo could not be found on storage."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            file_handle,
            content_type=content_type,
            as_attachment=False,
            filename=filename,
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


# 2. STAFF API — ADMINISTRATOR ONLY CRUD & DESK ACTIONS

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('-staff_id')
    serializer_class = StaffSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]

    def get_permissions(self):
        # Allow staff officers to retrieve desk summary
        if self.action == 'desk_summary':
            return [IsStaffOrAdministrator()]
        return [IsAdministrator()]

    def _get_admin(self):
        admin_id = getattr(self.request.user, 'user_id', None)
        if admin_id:
            try:
                return Administrator.objects.get(admin_id=admin_id)
            except Administrator.DoesNotExist:
                pass
        return None

    def perform_create(self, serializer):
        staff = serializer.save()
        admin = self._get_admin()
        if admin:
            ActivityLog.objects.create(
                administrator=admin,
                action_taken=f"Registered staff officer #{staff.staff_id}: {staff.full_name} ({staff.username or staff.email}) in {staff.department}"
            )

    def perform_update(self, serializer):
        staff = serializer.save()
        admin = self._get_admin()
        if admin:
            status_label = "Active" if staff.is_active and staff.status == "Active" else "Inactive"
            ActivityLog.objects.create(
                administrator=admin,
                action_taken=f"Updated staff officer #{staff.staff_id}: {staff.full_name} ({status_label})"
            )

    def perform_destroy(self, instance):
        admin = self._get_admin()
        staff_info = f"#{instance.staff_id} ({instance.full_name})"
        if admin:
            ActivityLog.objects.create(
                administrator=admin,
                action_taken=f"Deleted staff officer {staff_info}"
            )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        staff = self.get_object()
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {"new_password": ["A new password is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            validate_password(new_password, user=staff)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        staff.password = new_password
        staff.save()

        admin = self._get_admin()
        if admin:
            ActivityLog.objects.create(
                administrator=admin,
                action_taken=f"Reset password for staff officer #{staff.staff_id} ({staff.full_name})"
            )

        return Response(
            {"message": f"Password reset successfully for staff officer {staff.full_name}."},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='desk-summary')
    def desk_summary(self, request):
        """Real-time desk statistics for the staff officer workspace"""
        user = request.user
        staff_id = getattr(user, 'user_id', None)
        user_type = getattr(user, 'user_type', None)

        apps = Application.objects.all()
        assigned_apps = apps.filter(staff_id=staff_id) if (user_type == 'staff' and staff_id) else apps

        q_tokens = QueueToken.objects.all()
        q_waiting = q_tokens.filter(queue_status='Waiting').count()
        q_serving = q_tokens.filter(queue_status='Serving').count()
        q_completed = q_tokens.filter(queue_status='Completed').count()

        pending_verifications = apps.filter(status__in=['Pending', 'Under Review']).count()
        completed_apps = apps.filter(status__in=['Approved', 'Completed']).count()

        docs = Document.objects.all()
        pending_docs = docs.filter(verification_status='Pending').count()
        verified_docs = docs.filter(verification_status='Verified').count()

        payments = Payment.objects.filter(Q(status='VERIFIED') | Q(payment_status='Completed')).count()

        current_token = q_tokens.filter(queue_status__in=['Called', 'Serving']).order_by('-called_time').first()
        current_token_data = QueueTokenSerializer(current_token).data if current_token else None

        return Response({
            "assigned_count": assigned_apps.count(),
            "pending_verifications": pending_verifications,
            "completed_count": completed_apps,
            "queue_waiting": q_waiting,
            "queue_serving": q_serving,
            "queue_completed": q_completed,
            "pending_documents": pending_docs,
            "verified_documents": verified_docs,
            "verified_payments": payments,
            "current_token": current_token_data
        }, status=status.HTTP_200_OK)


class AdministratorViewSet(viewsets.ModelViewSet):
    queryset = Administrator.objects.all().order_by('-admin_id')
    serializer_class = AdministratorSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]

    def destroy(self, request, *args, **kwargs):
        administrator = self.get_object()
        current_id = getattr(request.user, 'user_id', None)
        if administrator.admin_id == current_id:
            return Response(
                {"error": "You cannot delete the administrator account used by this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if administrator.is_active and Administrator.objects.filter(is_active=True).count() <= 1:
            return Response(
                {"error": "The final active administrator account cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='system-summary')
    def system_summary(self, request):
        """
        Comprehensive real-time system metrics aggregated directly from PostgreSQL.
        Used by the Central Administrator Dashboard.
        """
        from decimal import Decimal
        from django.db.models import Sum

        total_applicants = Applicant.objects.count()
        apps = Application.objects.all()
        total_apps = apps.count()
        pending_apps = apps.filter(status='Pending').count()
        review_apps = apps.filter(status='Under Review').count()
        approved_apps = apps.filter(status='Approved').count()
        completed_apps = apps.filter(status='Completed').count()
        rejected_apps = apps.filter(status='Rejected').count()

        staff_qs = Staff.objects.all()
        total_staff = staff_qs.count()
        active_staff = staff_qs.filter(is_active=True, status='Active').count()

        q_tokens = QueueToken.objects.all()
        q_waiting = q_tokens.filter(queue_status='Waiting').count()
        q_serving = q_tokens.filter(queue_status='Serving').count()
        q_completed = q_tokens.filter(queue_status='Completed').count()

        payments = Payment.objects.all()
        verified_payments = payments.filter(Q(status='VERIFIED') | Q(payment_status='Completed'))
        total_revenue = verified_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        verified_count = verified_payments.count()
        pending_payments_count = payments.filter(
            Q(status__in=['PENDING', 'QR_GENERATED', 'PAYMENT_INITIATED']) | Q(payment_status='Pending')
        ).count()

        docs = Document.objects.all()
        total_docs = docs.count()
        verified_docs = docs.filter(verification_status='Verified').count()
        pending_docs = docs.filter(verification_status='Pending').count()
        rejected_docs = docs.filter(verification_status='Rejected').count()

        sigs = DigitalSignature.objects.filter(is_valid=True).count()

        return Response({
            "total_applicants": total_applicants,
            "total_applications": total_apps,
            "pending_applications": pending_apps,
            "under_review_applications": review_apps,
            "approved_applications": approved_apps,
            "completed_applications": completed_apps,
            "rejected_applications": rejected_apps,
            "total_staff": total_staff,
            "active_staff": active_staff,
            "queue_waiting": q_waiting,
            "queue_serving": q_serving,
            "queue_completed": q_completed,
            "verified_payments_count": verified_count,
            "pending_payments_count": pending_payments_count,
            "total_revenue": float(total_revenue),
            "total_documents": total_docs,
            "verified_documents": verified_docs,
            "pending_documents": pending_docs,
            "rejected_documents": rejected_docs,
            "valid_signatures": sigs
        }, status=status.HTTP_200_OK)



class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by('-application_id')
    serializer_class = ApplicationSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return Application.objects.filter(applicant_id=user_id).order_by('-application_id')
        return Application.objects.all().order_by('-application_id')

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        # Enforce ONE APPLICANT = ONE APPLICATION / PASSPORT RULE
        applicant_id_to_check = user_id if user_type == 'applicant' else (
            self.request.data.get('applicant') or
            serializer.validated_data.get('applicant_id') or
            (serializer.validated_data.get('applicant').applicant_id if serializer.validated_data.get('applicant') else None)
        )

        category = self.request.data.get('passport_category') or serializer.validated_data.get('passport_category') or 'Ordinary (34 Pages)'
        service_type = self.request.data.get('service_type') or serializer.validated_data.get('service_type') or 'New Passport'
        app_type = self.request.data.get('application_type') or serializer.validated_data.get('application_type')
        if not app_type:
            app_type = 'RENEWAL' if 'renewal' in (service_type or '').lower() else 'NEW'
        is_renewal_request = (app_type == 'RENEWAL' or 'renewal' in (service_type or '').lower())

        if not applicant_id_to_check:
            raise ValidationError({'applicant': 'A valid citizen is required.'})

        if applicant_id_to_check:
            # Serialize application creation per citizen. This closes the race
            # between the active-application check and the INSERT below.
            Applicant.objects.select_for_update().get(
                applicant_id=applicant_id_to_check
            )
            existing_apps = Application.objects.filter(applicant_id=applicant_id_to_check)

            # Pending/review records and unsigned pre-payment approvals are
            # active applications. A signed Approved record is an issued
            # passport and is handled by the expiry/renewal rules below.
            active_app = existing_apps.filter(
                status__in=['Pending', 'Under Review']
            ).first()
            if not active_app:
                for approved_app in existing_apps.filter(status='Approved').order_by('-application_id'):
                    signature = getattr(approved_app, 'digital_signature', None)
                    if not (signature and signature.is_valid and approved_app.expiry_date):
                        active_app = approved_app
                        break
            if active_app:
                raise ValidationError({
                    "error": "You already have a passport application.",
                    "detail": f"You cannot submit another application. Active application #NP-{active_app.application_id:04d} is currently '{active_app.status}'.",
                    "application_id": active_app.application_id,
                    "status": active_app.status
                })

            rejected_app = existing_apps.filter(status='Rejected').order_by(
                '-application_id'
            ).first()
            if rejected_app:
                raise ValidationError({
                    "error": "Your existing application requires correction.",
                    "detail": (
                        f"Application #NP-{rejected_app.application_id:04d} is rejected. "
                        "Upload a replacement for each rejected document instead of creating "
                        "a new application."
                    ),
                    "application_id": rejected_app.application_id,
                    "status": rejected_app.status,
                })

            # CASE 5: Final issuance intentionally displays Approved. Retain
            # support for older Completed records as well.
            completed_passports = existing_apps.filter(
                status__in=['Approved', 'Completed'],
                digital_signature__is_valid=True,
                expiry_date__isnull=False,
            ).order_by('-application_id')
            latest_completed = completed_passports.first()

            if latest_completed:
                p_status = latest_completed.passport_status
                if p_status == 'ACTIVE':
                    exp_date_str = str(latest_completed.expiry_date) if latest_completed.expiry_date else 'Active'
                    raise ValidationError({
                        "error": "You already have a passport application.",
                        "detail": f"You already have an active valid passport (Valid until {exp_date_str}). Renewal is only permitted after your passport expires.",
                        "application_id": latest_completed.application_id,
                        "passport_status": "ACTIVE",
                        "expiry_date": exp_date_str
                    })
                elif p_status == 'EXPIRED':
                    # CASE 6: Passport has expired - reject normal new application, allow renewal
                    if not is_renewal_request:
                        raise ValidationError({
                            "error": "Your previous passport has expired. You must apply for a Renewal through the Renewal workflow, not a new passport application.",
                            "detail": "Standard new passport applications are not permitted when an expired passport exists. Please apply through the Renewal workflow.",
                            "application_id": latest_completed.application_id,
                            "passport_status": "EXPIRED"
                        })
            else:
                if is_renewal_request:
                    raise ValidationError({
                        "error": "Cannot apply for passport renewal without a previously completed passport.",
                        "detail": "Please apply for a New Passport."
                    })

        if is_renewal_request:
            app_type = 'RENEWAL'
            if 'renewal' not in (service_type or '').lower():
                service_type = 'Passport Renewal'
        else:
            app_type = 'NEW'

        if user_type == 'applicant':
            app = serializer.save(
                applicant_id=user_id,
                passport_category=category,
                service_type=service_type,
                application_type=app_type,
                biometric_status='Pending',
                status='Pending',
                staff=None,
                processing_notes='',
                issue_date=None,
                expiry_date=None,
            )
        else:
            app = serializer.save(
                passport_category=category,
                service_type=service_type,
                application_type=app_type,
                biometric_status='Pending',
                status='Pending',
                processing_notes='',
                issue_date=None,
                expiry_date=None,
            )


        # 1. Provision the fee assessment. The citizen can pay only after the
        # required document uploads; the processing token is created later,
        # after biometrics and digital signature authorization.
        if not Payment.objects.filter(application=app).exists():
            applicant_inst = getattr(app, 'applicant', None)
            fee = app.fee_amount
            Payment.objects.create(
                application=app,
                applicant=applicant_inst,
                amount=fee,
                currency='NPR',
                payment_method='eSewa',
                transaction_id=f"ASSESS-{app.application_id:04d}-{secrets.token_hex(3).upper()}",
                payment_status='Pending',
                remarks=f"Fee assessment for {category}"
            )

        # 2. Provision initial confirmation Notification for applicant
        applicant_inst = getattr(app, 'applicant', None)
        if applicant_inst:
            Notification.objects.create(
                applicant=applicant_inst,
                application=app,
                type='Application Submitted',
                message=(
                    f"Application #NP-{app.application_id:04d} ({category}) submitted successfully. "
                    f"Your private tracking reference is {app.tracking_reference}. "
                    "Upload the required documents, then complete payment."
                ),
                status='Unread'
            )

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        instance_id = self.get_object().application_id
        instance = Application.objects.select_for_update().select_related(
            'applicant'
        ).get(application_id=instance_id)
        serializer.instance = instance

        # A submitted application is an official record. Citizens use the
        # document replacement workflow instead of mutating application data.
        if user_type == 'applicant':
            raise PermissionDenied("Submitted applications cannot be modified by applicants.")

        allowed_fields = {
            'status',
            'staff',
            'processing_notes',
            'appointment_date',
            'appointment_time',
            'appointment_office',
        }
        protected_fields = set(self.request.data.keys()) - allowed_fields
        if protected_fields:
            raise ValidationError({
                'error': (
                    'Submitted identity, passport, payment, biometric, and issuance fields '
                    'cannot be changed through the general application endpoint.'
                )
            })

        # Check approval rule: CANNOT transition to 'Approved' unless all required documents exist and are verified!
        target_status = self.request.data.get('status') or serializer.validated_data.get('status')
        if target_status and target_status != instance.status:
            allowed_transitions = {
                'Pending': {'Under Review'},
                'Under Review': {'Pending'},
                'Approved': set(),
                'Rejected': set(),
                'Completed': set(),
            }
            if target_status not in allowed_transitions.get(instance.status, set()):
                raise ValidationError({
                    'status': (
                        f"Application cannot change from {instance.status} to {target_status}. "
                        'Use the document replacement, payment, biometric, or signature workflow.'
                    )
                })

            signature = getattr(instance, 'digital_signature', None)
            if signature and signature.is_valid:
                raise ValidationError({
                    'status': 'A digitally signed application has a final status and cannot be changed here.'
                })

        if target_status == 'Rejected' and instance.status != 'Rejected':
            reason = str(
                self.request.data.get('processing_notes')
                or serializer.validated_data.get('processing_notes')
                or ''
            ).strip()
            if not reason:
                raise ValidationError({
                    'processing_notes': 'A clear rejection reason is required.'
                })
            if not any(
                document.verification_status == 'Rejected'
                for document in instance.get_current_documents()
            ):
                raise ValidationError({
                    'status': (
                        'Reject the specific invalid document. The application will be '
                        'rejected automatically and the citizen can upload a replacement.'
                    )
                })
            if instance.payments.filter(
                Q(status='VERIFIED') | Q(payment_status='Completed')
            ).exists():
                raise ValidationError({
                    'status': 'A paid application cannot be rejected through the general status endpoint.'
                })

        if target_status == 'Approved' and instance.status != 'Approved':
            raise ValidationError({
                "status": (
                    "Final approval is issued only after verified payment, all current "
                    "documents, biometrics, and the government digital signature."
                )
            })

        if target_status == 'Completed' and instance.status != 'Completed':
            raise ValidationError({
                "status": "Application completion is controlled by the passport issuance workflow."
            })

        old_status = instance.status
        app = serializer.save()
        new_status = app.status

        # If status changed, create Notification and ActivityLog
        if old_status != new_status:
            if app.applicant:
                try:
                    Notification.objects.create(
                        applicant=app.applicant,
                        application=app,
                        type='Application Status Update',
                        message=f"Application #NP-{app.application_id:04d} status updated from '{old_status}' to '{new_status}'.",
                        status='Unread'
                    )
                except Exception:
                    pass

            # Log staff/admin activity
            try:
                actor_staff = None
                actor_admin = None
                if user_type == 'staff':
                    actor_staff = Staff.objects.filter(staff_id=user_id).first()
                elif user_type == 'administrator':
                    actor_admin = Administrator.objects.filter(admin_id=user_id).first()

                if actor_staff or actor_admin:
                    actor_str = f"Staff #{actor_staff.staff_id}" if actor_staff else f"Admin #{actor_admin.admin_id}"
                    ActivityLog.objects.create(
                        administrator=actor_admin,
                        application=app,
                        action_taken=f"[{actor_str}] Status changed to '{new_status}' (from '{old_status}')"[:255]
                    )
            except Exception:
                pass

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "Application records are retained for audit history and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['get'], url_path='workflow-status')
    def workflow_status(self, request, pk=None):
        """
        Returns the granular 9-step workflow state for a specific application.
        """
        app = self.get_object()
        facts = build_workflow_facts(app)

        return Response({
            "application_id": app.application_id,
            "reference": f"NP-{app.application_id:04d}",
            "status": app.status,
            "passport_category": app.passport_category,
            "passport_type": app.passport_type,
            "passport_pages": app.passport_pages,
            "delivery_type": app.delivery_type,
            "service_type": app.service_type,
            "biometric_status": getattr(app, 'biometric_status', 'Pending'),
            "fee_amount": app.fee_amount,
            "queue_position": app.queue_position,
            "submission_date": app.submission_date,
            "last_updated": app.last_updated,
            "passport_number": app.passport_number,
            "can_download_pdf": facts['can_download'],
            "steps": app.get_workflow_steps()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='current-workflow', permission_classes=[AllowAny])
    def current_workflow(self, request):
        """
        Returns the 9-step workflow state for the logged-in applicant's latest application.
        If no application exists yet, returns a starter state.
        """
        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        if user_type == 'applicant' and user_id:
            latest_app = Application.objects.filter(applicant_id=user_id).order_by('-application_id').first()
            if latest_app:
                steps = latest_app.get_workflow_steps()
                facts = build_workflow_facts(latest_app)

                # Document summary and photo inspection
                docs = facts['documents']
                total_docs = len(docs)
                verified_docs = sum(1 for d in docs if d.verification_status == 'Verified')
                rejected_docs_count = sum(1 for d in docs if d.verification_status == 'Rejected')
                pending_docs = sum(1 for d in docs if d.verification_status == 'Pending')

                photo_doc = next((d for d in docs if 'photo' in (d.document_type or '').lower()), None)
                has_photo = bool(photo_doc)
                photo_verified = bool(photo_doc and photo_doc.verification_status == 'Verified')
                photo_rejected = bool(photo_doc and photo_doc.verification_status == 'Rejected')
                has_identity = any(
                    any(label in (document.document_type or '').casefold()
                        for label in ('citizenship', 'national id', 'nid'))
                    for document in docs
                )

                # Active payment info — STRICT PAYMENT GATE (backend source of truth)
                payment_reference = None
                payment_status_val = None
                is_payment_verified = facts['payment_verified']
                try:
                    from django.db.models import Q
                    active_pay = latest_app.payments.order_by('-payment_id').first()
                    if active_pay:
                        payment_reference = active_pay.payment_reference
                        payment_status_val = active_pay.status
                except Exception:
                    pass

                sig = facts['signature']
                is_sig_valid = facts['signature_is_valid']
                queue_token_info = facts['queue_token_info']
                can_download = facts['can_download']

                # Queue token info

                doc_summary = {
                    'total': total_docs,
                    'verified': verified_docs,
                    'rejected': rejected_docs_count,
                    'pending': pending_docs,
                    'has_photo': has_photo,
                    'photo_verified': photo_verified,
                    'has_identity_document': has_identity,
                }

                # Rejected doc details
                rejected_docs = [{
                    'document_id': d.document_id,
                    'document_type': d.document_type,
                    'rejection_reason': d.rejection_reason or 'Document quality or authenticity issue.',
                } for d in docs if d.verification_status == 'Rejected']

                # Authoritative serial current_step determination
                is_approved = (latest_app.status == 'Approved')
                is_completed = (latest_app.status == 'Completed')
                all_current_documents_verified = bool(
                    total_docs > 0
                    and has_photo
                    and has_identity
                    and verified_docs == total_docs
                )
                if total_docs == 0 or not has_photo or not has_identity or rejected_docs_count > 0:
                    current_step_key = 'documents'
                elif not is_payment_verified:
                    current_step_key = 'fee'
                elif not all_current_documents_verified:
                    current_step_key = 'verification'
                elif getattr(latest_app, 'biometric_status', None) != 'Verified':
                    current_step_key = 'biometrics'
                elif not is_sig_valid:
                    current_step_key = 'signature'
                elif not queue_token_info or queue_token_info['queue_status'] != 'Completed':
                    current_step_key = 'queue'
                else:
                    current_step_key = 'passport_ready'

                photo_url = (
                    f"/api/applicants/{latest_app.applicant_id}/profile-photo/"
                    if photo_verified else None
                )

                return Response({
                    "has_application": True,
                    "application_id": latest_app.application_id,
                    "reference": f"NP-{latest_app.application_id:04d}",
                    "status": latest_app.status,
                    "passport_category": latest_app.passport_category,
                    "passport_type": latest_app.passport_type,
                    "passport_pages": latest_app.passport_pages,
                    "delivery_type": latest_app.delivery_type,
                    "service_type": latest_app.service_type,
                    "application_type": getattr(latest_app, 'application_type', 'NEW'),
                    "issue_date": str(latest_app.issue_date) if latest_app.issue_date else None,
                    "expiry_date": str(latest_app.expiry_date) if latest_app.expiry_date else None,
                    "passport_status": latest_app.passport_status,
                    "passport_number": latest_app.passport_number,
                    "is_expired": latest_app.is_expired,
                    "biometric_status": getattr(latest_app, 'biometric_status', 'Pending'),
                    "fee_amount": latest_app.fee_amount,
                    "queue_position": latest_app.queue_position,
                    "submission_date": latest_app.submission_date,
                    "last_updated": latest_app.last_updated,
                    "can_download_pdf": can_download,
                    "current_step": current_step_key,
                    "is_payment_verified": is_payment_verified,
                    "is_signature_verified": is_sig_valid,
                    "has_photo": has_photo,
                    "photo_verified": photo_verified,
                    "has_identity_document": has_identity,
                    "photo_rejected": photo_rejected,
                    "photo_rejection_reason": photo_doc.rejection_reason if photo_doc else None,
                    "photo_url": photo_url,
                    "payment_reference": payment_reference,
                    "payment_status": payment_status_val,
                    "queue_token": queue_token_info,
                    "document_summary": doc_summary,
                    "rejected_docs": rejected_docs,
                    "steps": steps
                }, status=status.HTTP_200_OK)


            # Logged in, but hasn't submitted an application yet
            applicant_obj = Applicant.objects.filter(applicant_id=user_id).first()
            citizen_name = applicant_obj.full_name if applicant_obj else "Citizen User"
            default_steps = [
                {"step": 1, "key": "registration", "title": "Citizen Registration / Login", "status": "Completed", "details": f"Registered citizen: {citizen_name}", "action_url": "/applicant/profile/", "action_label": "View Profile"},
                {"step": 2, "key": "application", "title": "Fill Application", "status": "Action Required", "details": "Please complete your passport application form", "action_url": "/applicant/apply/", "action_label": "Start Application"},
                {"step": 3, "key": "documents", "title": "Upload Required Documents", "status": "Not Started", "details": "Upload Citizenship or National ID and a passport photo", "action_url": "/applicant/documents/", "action_label": "Upload Documents"},
                {"step": 4, "key": "fee", "title": "Payment", "status": "Not Started", "details": "Complete payment after the required uploads", "action_url": "/applicant/apply/", "action_label": "Payment"},
                {"step": 5, "key": "verification", "title": "Staff Document Verification", "status": "Not Started", "details": "Staff inspect and decide every current document", "action_url": "/applicant/dashboard/", "action_label": "Track Review"},
                {"step": 6, "key": "biometrics", "title": "Biometrics Verification", "status": "Not Started", "details": "Authorized staff complete biometric verification", "action_url": "/applicant/documents/", "action_label": "Biometrics"},
                {"step": 7, "key": "signature", "title": "Digital Signature", "status": "Not Started", "details": "Government digital signature authorization", "action_url": "/applicant/dashboard/", "action_label": "Signature"},
                {"step": 8, "key": "queue", "title": "Queue / Processing", "status": "Not Started", "details": "A processing token is assigned after digital signing", "action_url": "/applicant/queue/", "action_label": "Queue Info"},
                {"step": 9, "key": "passport_ready", "title": "Passport Generation", "status": "Not Started", "details": "Generated after queue processing is completed", "action_url": "/applicant/dashboard/", "action_label": "Virtual Passport", "can_download": False}
            ]
            return Response({
                "has_application": False,
                "application_id": None,
                "reference": None,
                "status": "Not Started",
                "can_download_pdf": False,
                "current_step": "application",
                "payment_reference": None,
                "payment_status": None,
                "queue_token": None,
                "document_summary": {"total": 0, "verified": 0, "rejected": 0, "pending": 0},
                "rejected_docs": [],
                "steps": default_steps
            }, status=status.HTTP_200_OK)

        # For unauthenticated or non-applicant users
        guest_steps = [
            {"step": 1, "key": "registration", "title": "Citizen Registration / Login", "status": "Action Required", "details": "Create a citizen account or sign in", "action_url": "/register/", "action_label": "Register Now"},
            {"step": 2, "key": "application", "title": "Fill Application", "status": "Not Started", "details": "Complete digital e-passport application", "action_url": "/login/", "action_label": "Sign In"},
            {"step": 3, "key": "documents", "title": "Upload Required Documents", "status": "Not Started", "details": "Upload identity evidence and passport photo", "action_url": "/login/", "action_label": "Sign In"},
            {"step": 4, "key": "fee", "title": "Payment", "status": "Not Started", "details": "Pay securely after uploading the required documents", "action_url": "/#services", "action_label": "View Tariffs"},
            {"step": 5, "key": "verification", "title": "Staff Document Verification", "status": "Not Started", "details": "Staff inspect and verify every required document", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 6, "key": "biometrics", "title": "Biometrics Verification", "status": "Not Started", "details": "Authorized biometric verification", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 7, "key": "signature", "title": "Digital Signature", "status": "Not Started", "details": "Government digital signature authorization", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 8, "key": "queue", "title": "Queue / Processing", "status": "Not Started", "details": "Processing token assignment and service", "action_url": "/track/", "action_label": "Track Queue"},
            {"step": 9, "key": "passport_ready", "title": "Passport Generation", "status": "Not Started", "details": "Passport generated after processing completes", "action_url": "/login/", "action_label": "Citizen Login", "can_download": False}
        ]
        return Response({
            "has_application": False,
            "application_id": None,
            "reference": None,
            "status": "Not Started",
            "can_download_pdf": False,
            "current_step": "registration",
            "payment_reference": None,
            "payment_status": None,
            "queue_token": None,
            "document_summary": {"total": 0, "verified": 0, "rejected": 0, "pending": 0},
            "rejected_docs": [],
            "steps": guest_steps
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf', permission_classes=[IsAuthenticated])
    def download_pdf(self, request, pk=None):
        """
        Generates and serves the official Virtual Passport PDF certificate.
        Strictly gated:
        1. Application exists and user authorized.
        2. Application status is Approved or Completed.
        3. Required documents (Citizenship & Passport Photo) are verified.
        4. Payment is verified by the backend (STRICT PAYMENT GATE).
        5. Government digital signature is authorized and valid.
        6. Queue processing is completed.
        """
        app = self.get_object()

        # Permission check: applicant can download their own, staff/admin can download any
        user = getattr(request, 'user', None)
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        if user_type == 'applicant' and app.applicant_id != user_id:
            return Response({"error": "You are not authorized to download this passport."}, status=status.HTTP_403_FORBIDDEN)
        if user_type not in ['applicant', 'staff', 'administrator']:
            return Response({"error": "You are not authorized to download this passport."}, status=status.HTTP_403_FORBIDDEN)

        if app.status not in ['Approved', 'Completed']:
            return Response(
                {"error": f"Virtual Passport is not yet ready. Current application status is '{app.status}'. All previous stages must be completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Check required documents & verified passport-size photo
        docs = app.get_current_documents()
        photo_doc = next((d for d in docs if 'photo' in (d.document_type or '').lower()), None)
        if not photo_doc:
            return Response(
                {"error": "Passport-size photo is required before continuing."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if photo_doc.verification_status != 'Verified':
            return Response(
                {"error": "Passport photo is awaiting verification."},
                status=status.HTTP_400_BAD_REQUEST
            )

        has_verified_identity = any(
            document.verification_status == 'Verified'
            and any(label in (document.document_type or '').casefold()
                    for label in ('citizenship', 'national id', 'nid'))
            for document in docs
        )
        if not has_verified_identity:
            return Response(
                {"error": "A verified Citizenship Certificate or National ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unverified_docs = [d for d in docs if d.verification_status != 'Verified']
        if unverified_docs:
            return Response(
                {"error": "All current required documents must be verified by staff before passport issuance."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. STRICT PAYMENT GATE
        from django.db.models import Q
        verified_payment = app.payments.filter(
            Q(status='VERIFIED') | Q(payment_status='Completed')
        ).first()
        if not verified_payment:
            return Response(
                {"error": "Complete payment. Virtual Passport cannot be issued or downloaded before payment is verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if getattr(app, 'biometric_status', None) != 'Verified':
            return Response(
                {"error": "Biometric verification must be completed before passport issuance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Check Government Digital Signature
        sig = getattr(app, 'digital_signature', None)
        try:
            signature_is_valid = bool(sig and verify_signature(sig))
        except SigningConfigurationError:
            return Response(
                {"error": "Passport signature verification is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not signature_is_valid:
            return Response(
                {"error": "The passport does not have a valid cryptographic signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queue_token = getattr(app, 'queue_token', None)
        if not queue_token or queue_token.queue_status != 'Completed':
            return Response(
                {"error": "Queue processing must be completed before passport generation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not app.passport_number:
            return Response(
                {"error": "A sequential passport number has not been assigned yet."},
                status=status.HTTP_409_CONFLICT,
            )

        # Record issue date and expiry date if not yet set

        if not app.issue_date:
            from django.conf import settings
            validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
            app.issue_date = timezone.localdate()
            app.expiry_date = app.issue_date.replace(year=app.issue_date.year + validity)
            app.save(update_fields=['issue_date', 'expiry_date'])

        try:
            pdf_bytes = generate_passport_pdf(app)

            filename = f"Virtual_Passport_{app.passport_number}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        except Exception:
            logger.exception('Failed to generate passport PDF for application %s.', app.application_id)
            return Response(
                {"error": "The passport PDF could not be generated. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'], url_path='generate_pdf', permission_classes=[IsAuthenticated])
    def generate_pdf(self, request, pk=None):
        """Alias for download_pdf."""
        return self.download_pdf(request, pk=pk)

    @action(detail=True, methods=['post'], url_path='verify-biometrics')
    @transaction.atomic
    def verify_biometrics(self, request, pk=None):
        """
        Staff or Admin action to update application biometric matching status.
        Supported statuses: 'Verified', 'Failed', 'Submitted', 'Pending'.
        """
        user_type = getattr(request.user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can verify biometrics."}, status=status.HTTP_403_FORBIDDEN)

        app_id = self.get_object().application_id
        app = Application.objects.select_for_update().select_related(
            'applicant'
        ).get(application_id=app_id)
        new_status = request.data.get('biometric_status')
        valid_choices = [c[0] for c in Application.BIOMETRIC_STATUS_CHOICES]
        if new_status not in valid_choices:
            return Response({"error": f"Invalid biometric_status. Must be one of: {', '.join(valid_choices)}"}, status=status.HTTP_400_BAD_REQUEST)

        signature = getattr(app, 'digital_signature', None)
        if signature and signature.is_valid and new_status != app.biometric_status:
            return Response(
                {"error": "Biometrics are final after the application has been digitally signed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_transitions = {
            'Pending': {'Submitted', 'Verified', 'Failed'},
            'Submitted': {'Verified', 'Failed'},
            'Failed': {'Submitted'},
            'Verified': set(),
        }
        if (
            new_status != app.biometric_status
            and new_status not in allowed_transitions.get(app.biometric_status, set())
        ):
            return Response(
                {
                    "error": (
                        f"Biometric status cannot change from {app.biometric_status} "
                        f"to {new_status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            new_status != app.biometric_status
            and new_status in {'Submitted', 'Verified', 'Failed'}
        ):
            is_paid = app.payments.filter(
                Q(status='VERIFIED') | Q(payment_status='Completed')
            ).exists()
            if not is_paid:
                return Response(
                    {"error": "Payment must be verified before biometric review can begin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not _current_document_review_is_complete(app):
                return Response(
                    {"error": "All current required documents must be verified before biometric review can begin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        notes = request.data.get('remarks', '').strip()
        app.biometric_status = new_status
        if app.payments.filter(
            Q(status='VERIFIED') | Q(payment_status='Completed')
        ).exists():
            signature = getattr(app, 'digital_signature', None)
            if app.status == 'Approved' and not (signature and signature.is_valid):
                app.status = 'Pending'
        if notes:
            app.processing_notes = f"{app.processing_notes or ''}\n[Biometrics]: {notes}".strip()
        app.save()

        # Notify citizen
        if app.applicant:
            try:
                Notification.objects.create(
                    applicant=app.applicant,
                    application=app,
                    type='Biometrics Update',
                    message=f"Biometric matching for application #NP-{app.application_id:04d} updated to '{new_status}'.",
                    status='Unread'
                )
            except Exception:
                pass

        return Response({
            "message": f"Biometric match status updated to '{new_status}'.",
            "biometric_status": new_status,
            "application_id": app.application_id
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='authorize-signature')
    @transaction.atomic
    def authorize_signature(self, request, pk=None):
        """
        Staff or Administrator authorization to issue Government Digital Signature.
        Strictly gated by current documents, payment, biometric verification, and identity checks.
        """
        user_type = getattr(request.user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only authorized Staff or Administrator can issue digital signatures."}, status=status.HTTP_403_FORBIDDEN)

        app_id = self.get_object().application_id
        app = Application.objects.select_for_update().select_related(
            'applicant'
        ).get(application_id=app_id)

        # STRICT PAYMENT GATE: Payment must be verified prior to digital signature authorization
        from django.db.models import Q
        is_paid = app.payments.filter(Q(status='VERIFIED') | Q(payment_status='Completed')).exists()
        if not is_paid:
            return Response(
                {"error": "Payment has not been verified yet. Applications cannot be signed or issued before verified payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # STRICT DOCUMENT GATE: every current document version must be verified.
        docs = app.get_current_documents()
        if not docs:
            return Response(
                {"error": "Required documents must be uploaded before signature authorization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        unverified_docs = [d for d in docs if d.verification_status != 'Verified']
        if unverified_docs:
            return Response(
                {"error": "All current documents must be verified before signature authorization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        photo_doc = next((d for d in docs if (d.document_type or '').strip() == 'Passport Photo'), None)
        if not photo_doc:
            return Response(
                {"error": "A verified Passport Photo is required before signature authorization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        has_verified_identity = any(
            document.verification_status == 'Verified'
            and any(label in (document.document_type or '').casefold()
                    for label in ('citizenship', 'national id', 'nid'))
            for document in docs
        )
        if not has_verified_identity:
            return Response(
                {"error": "A verified Citizenship Certificate or National ID is required before signature authorization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if getattr(app, 'biometric_status', None) != 'Verified':
            return Response(
                {"error": "Biometrics must be verified before signature authorization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sig = getattr(app, 'digital_signature', None)
            if not (sig and sig.is_valid):
                # Validity dates are part of the signed canonical payload. Fix
                # them before signing, but do not activate or expose the
                # passport until processing is completed.
                if not app.issue_date:
                    from django.conf import settings
                    validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
                    app.issue_date = timezone.localdate()
                    app.expiry_date = app.issue_date.replace(
                        year=app.issue_date.year + validity
                    )
                    app.save(update_fields=['issue_date', 'expiry_date', 'last_updated'])
                sig = _sign_application_record(app)

            token = _ensure_processing_queue_token(app)
            if token.queue_status != 'Completed' and app.status != 'Pending':
                app.status = 'Pending'
                app.processing_notes = (
                    'Digital signature authorized. Queue processing is pending.'
                )
                app.save(update_fields=['status', 'processing_notes', 'last_updated'])
        except SigningConfigurationError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Notify citizen
        if app.applicant:
            try:
                Notification.objects.create(
                    applicant=app.applicant,
                    application=app,
                    type='Digital Signature Authorized',
                    message=(
                        f"Government Digital Signature authorized for application "
                        f"#NP-{app.application_id:04d}. Processing token "
                        f"T-{token.token_number:03d} is now {token.queue_status}."
                    ),
                    status='Unread'
                )
            except Exception:
                pass

        return Response({
            "message": (
                f"Government Digital Signature authorized. Application "
                f"#NP-{app.application_id:04d} is now queued for processing."
            ),
            "certificate_serial": sig.certificate_serial,
            "signature_hash": sig.signature_hash,
            "verification_code": str(sig.verification_code),
            "verification_path": f"/api/signatures/verify/{sig.verification_code}/",
            "status": app.status,
            "queue_token": QueueTokenSerializer(token).data,
            "issue_date": str(app.issue_date) if app.issue_date else None,
            "expiry_date": str(app.expiry_date) if app.expiry_date else None,
            "passport_status": app.passport_status,
            "passport_number": app.passport_number,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='simulate-expiry')
    def simulate_expiry(self, request, pk=None):
        """
        Simulates passport expiry for testing and validation of the renewal workflow.
        Sets expiry_date to yesterday and status to Completed.
        """
        if not settings.DEBUG:
            return Response(
                {"error": "The development expiry simulator is disabled."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if getattr(request.user, 'user_type', None) != 'administrator':
            return Response(
                {"error": "Only administrators can use the development expiry simulator."},
                status=status.HTTP_403_FORBIDDEN,
            )
        app = self.get_object()
        from django.utils import timezone
        from datetime import timedelta
        yesterday = timezone.localdate() - timedelta(days=1)
        app.expiry_date = yesterday
        if not app.issue_date:
            app.issue_date = yesterday - timedelta(days=3650)
        app.status = 'Completed'
        app.save(update_fields=['expiry_date', 'issue_date', 'status'])
        return Response({
            "message": f"Application #NP-{app.application_id:04d} passport expired on {yesterday}.",
            "application_id": app.application_id,
            "passport_status": app.passport_status,
            "expiry_date": str(app.expiry_date),
            "is_expired": app.is_expired
        }, status=status.HTTP_200_OK)



class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-document_id')
    serializer_class = DocumentSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    # Document records are append-only. Decisions happen only through the
    # explicit, transaction-protected inspection/verify/reject actions below.
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        queryset = Document.objects.select_related(
            'application',
            'application__applicant',
        ).order_by('-document_id')

        if user_type == 'applicant':
            queryset = queryset.filter(application__applicant_id=user_id)

        application_id = (
            self.request.query_params.get('application')
            or self.request.query_params.get('application_id')
        )
        if application_id:
            try:
                application_id = int(application_id)
                if application_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({
                    'application': 'A valid positive application ID is required.'
                })
            queryset = queryset.filter(application_id=application_id)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        application = serializer.validated_data.get('application')
        if not application:
            app_id = self.request.data.get('application')
            if app_id:
                application = Application.objects.filter(application_id=app_id).first()

        if not application:
            raise ValidationError("Valid application ID is required to upload documents.")

        if user_type == 'applicant' and application.applicant_id != user_id:
            raise PermissionDenied("You can only upload documents for your own application.")

        doc_type = serializer.validated_data.get('document_type') or self.request.data.get('document_type')
        uploaded_file = self.request.FILES.get('file_path')

        try:
            validate_uploaded_document(uploaded_file, doc_type)
        except UploadSecurityError as exc:
            raise ValidationError({"file_path": str(exc)}) from exc

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if doc_type == 'Passport Photo' and ext not in ['.jpg', '.jpeg', '.png']:
            raise ValidationError({"file_path": "Passport photograph must be in JPG, JPEG, or PNG format."})

        # Serialize uploads for an application so two clicks cannot create two
        # simultaneous "current" records. A rejected record is immutable and
        # retained; its correction is always a new Pending document.
        with transaction.atomic():
            locked_application = Application.objects.select_for_update().get(
                application_id=application.application_id
            )
            requested_type_group = locked_application.document_type_group(doc_type)
            locked_documents = Document.objects.select_for_update().filter(
                application=locked_application,
            ).order_by('-document_id')
            current_document = next((
                document for document in locked_documents
                if locked_application.document_type_group(document.document_type)
                == requested_type_group
            ), None)

            if current_document and current_document.verification_status == 'Pending':
                raise ValidationError({
                    'document_type': (
                        f'A pending {doc_type} upload already exists. Wait for the staff decision before uploading again.'
                    )
                })
            if current_document and current_document.verification_status == 'Verified':
                raise ValidationError({
                    'document_type': (
                        f'The current {doc_type} is already verified and cannot be replaced.'
                    )
                })

            fname = os.path.basename(getattr(uploaded_file, 'name', 'document.pdf'))
            doc = serializer.save(
                application=locked_application,
                file_path=uploaded_file,
                file_name=fname,
                verification_status='Pending',
                rejection_reason='',
                is_inspected=False,
            )

            is_replacement_upload = bool(
                current_document
                and current_document.verification_status == 'Rejected'
            )

            # The response marks replacement uploads, but processing queue
            # assignment remains locked until digital signature authorization.
            doc._is_replacement_upload = is_replacement_upload

            # A replacement reopens document review only after every current
            # rejection has been replaced. Historical rejected rows remain.
            if (
                current_document
                and current_document.verification_status == 'Rejected'
                and locked_application.status == 'Rejected'
            ):
                has_current_rejection = any(
                    document.verification_status == 'Rejected'
                    for document in locked_application.get_current_documents()
                )
                if not has_current_rejection:
                    locked_application.status = 'Pending'
                    locked_application.processing_notes = (
                        f'Replacement {doc.document_type} uploaded; staff verification is pending.'
                    )
                    locked_application.last_updated = timezone.now()
                    locked_application.save(
                        update_fields=['status', 'processing_notes', 'last_updated']
                    )

            try:
                ActivityLog.objects.create(
                    application=doc.application,
                    action_taken=(
                        ("Replacement document uploaded: " if is_replacement_upload else "Document uploaded: ")
                        + f"{doc.document_type} for application "
                        + f"#NP-{doc.application.application_id:04d}"
                    )[:255],
                )
            except Exception:
                pass

            if is_replacement_upload and locked_application.applicant:
                try:
                    Notification.objects.create(
                        applicant=locked_application.applicant,
                        application=locked_application,
                        type='Replacement Document Received',
                        message=(
                            f"Your replacement {doc.document_type} was received. "
                            "It is waiting for staff document verification."
                        ),
                        status='Unread',
                    )
                except Exception:
                    pass

    def perform_update(self, serializer):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        if user_type == 'applicant':
            for f in ['verification_status', 'rejection_reason', 'is_inspected']:
                if f in self.request.data:
                    raise PermissionDenied(f"Applicants are not authorized to modify '{f}'.")

        instance = self.get_object()
        new_status = serializer.validated_data.get('verification_status') or self.request.data.get('verification_status')
        if new_status == 'Verified' and not instance.is_inspected:
            if not (self.request.data.get('is_inspected') is True or serializer.validated_data.get('is_inspected') is True):
                raise ValidationError({"verification_status": "Document must be opened and visually inspected before verification."})

        serializer.save()

    @action(detail=True, methods=['get'], url_path='view-file')
    def view_file(self, request, pk=None):
        """
        Securely stream and display the actual uploaded document from Django media storage.
        Available to authorized Staff/Admin or the owner Citizen.
        Automatically tracks visual inspection when accessed by Staff.
        """
        doc = self.get_object()
        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        if user_type == 'applicant':
            if not doc.application or doc.application.applicant_id != user_id:
                raise PermissionDenied("You can only access documents for your own application.")
        elif user_type not in ['staff', 'administrator']:
            raise PermissionDenied("Authentication required to inspect documents.")

        if not doc.file_path:
            return Response({"error": "Document file not found on storage."}, status=status.HTTP_404_NOT_FOUND)
        try:
            file_exists = doc.file_path.storage.exists(doc.file_path.name)
        except (OSError, ValueError, NotImplementedError):
            file_exists = False
        if not file_exists:
            return Response({"error": "Document file not found on storage."}, status=status.HTTP_404_NOT_FOUND)

        # Automatically mark as inspected if staff or admin views it
        if user_type in ['staff', 'administrator']:
            if not doc.is_inspected:
                doc.is_inspected = True
                doc.save(update_fields=['is_inspected'])
                try:
                    actor_staff = Staff.objects.filter(staff_id=user_id).first() if user_type == 'staff' else None
                    actor_admin = Administrator.objects.filter(admin_id=user_id).first() if user_type == 'administrator' else None
                    actor_str = (
                        f"Staff #{actor_staff.staff_id}" if actor_staff
                        else f"Admin #{actor_admin.admin_id}" if actor_admin
                        else "Officer"
                    )
                    ActivityLog.objects.create(
                        administrator=actor_admin,
                        application=doc.application,
                        action_taken=f"[{actor_str}] Inspected {doc.document_type} for application #NP-{doc.application.application_id:04d}"[:255]
                    )
                except Exception:
                    pass

        import mimetypes
        content_type, _ = mimetypes.guess_type(doc.file_name or doc.file_path.name)
        if not content_type:
            ext = os.path.splitext(doc.file_path.name)[1].lower()
            if ext == '.pdf':
                content_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif ext == '.png':
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'

        from django.http import FileResponse
        try:
            f = doc.file_path.open('rb')
            filename = doc.file_name or os.path.basename(doc.file_path.name)
            response = FileResponse(f, content_type=content_type, as_attachment=False, filename=filename)
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['X-Content-Type-Options'] = 'nosniff'
            response['Cache-Control'] = 'private, no-store, max-age=0'
            return response
        except Exception:
            logger.exception('Failed to open document ID %s from storage.', doc.document_id)
            return Response(
                {"error": "The document file could not be opened. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    @action(detail=True, methods=['post'], url_path='mark-inspected')
    def mark_inspected(self, request, pk=None):
        """Inspection is recorded only when the protected file is actually opened."""
        return Response(
            {"error": "Open the document file to record a staff inspection."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], url_path='verify-document')
    def verify_document(self, request, pk=None):
        """Staff/Admin verification of a specific document"""
        user = request.user
        user_type = getattr(user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can verify documents."}, status=status.HTTP_403_FORBIDDEN)

        document_snapshot = self.get_object()
        document_id = document_snapshot.document_id
        application_review_complete = False
        payment_unlocked = False
        with transaction.atomic():
            application = Application.objects.select_for_update().get(
                application_id=document_snapshot.application_id
            )
            doc = Document.objects.select_for_update().select_related(
                'application',
                'application__applicant',
            ).get(document_id=document_id)

            app_id_req = request.data.get('application_id') or request.data.get('application')
            if app_id_req and str(doc.application_id) != str(app_id_req):
                return Response(
                    {"error": "Document does not belong to the requested application."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment_is_verified = application.payments.filter(
                Q(status='VERIFIED') | Q(payment_status='Completed')
            ).exists()
            if not payment_is_verified:
                return Response(
                    {"error": "Payment must be verified before staff can decide a document."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if doc.verification_status != 'Pending':
                return Response({
                    "error": (
                        f"This document already has a final {doc.verification_status} decision and cannot be verified. "
                        "A rejected document must be corrected with a new replacement upload."
                    ),
                    "document_id": doc.document_id,
                    "current_status": doc.verification_status,
                }, status=status.HTTP_400_BAD_REQUEST)

            if not doc.is_inspected:
                return Response({
                    "error": "Document must be opened and visually inspected before verification.",
                    "document_id": doc.document_id,
                    "current_status": doc.verification_status,
                    "is_inspected": False,
                }, status=status.HTTP_400_BAD_REQUEST)

            doc.verification_status = 'Verified'
            doc.rejection_reason = ''
            doc.save(update_fields=['verification_status', 'rejection_reason'])

            application_review_complete = _current_document_review_is_complete(
                application
            )
            has_replacement_history = Document.objects.filter(
                application=application,
                verification_status='Rejected',
            ).exists()
            signature = getattr(application, 'digital_signature', None)

            # Completing either the initial review or a correction cycle keeps
            # the application Pending for biometrics and final signing.
            if (
                application_review_complete
                and not (signature and signature.is_valid)
            ):
                target_status = 'Pending'
                status_changed = application.status != target_status
                application.status = target_status
                application.processing_notes = (
                    'All current required documents, including replacement uploads, '
                    'are verified. Awaiting biometric verification and digital signature.'
                    if has_replacement_history else
                    'All current required documents are verified. Awaiting biometric '
                    'verification and digital signature.'
                )
                application.last_updated = timezone.now()
                application.save(update_fields=[
                    'status',
                    'processing_notes',
                    'last_updated',
                ])

                if application.applicant:
                    try:
                        Notification.objects.create(
                            applicant=application.applicant,
                            application=application,
                            type='Document Verification Completed',
                            message=(
                                f"All required documents for application "
                                f"#NP-{application.application_id:04d} are verified. "
                                'Biometrics and digital signing are next.'
                            ),
                            status='Unread',
                        )
                    except Exception:
                        pass

            application_status = application.status
            user_id = getattr(user, 'user_id', None)
            actor_staff = Staff.objects.filter(staff_id=user_id).first() if user_type == 'staff' else None
            actor_admin = Administrator.objects.filter(admin_id=user_id).first() if user_type == 'administrator' else None
            actor_str = f"Staff #{actor_staff.staff_id}" if actor_staff else (f"Admin #{actor_admin.admin_id}" if actor_admin else "Officer")
            try:
                ActivityLog.objects.create(
                    administrator=actor_admin,
                    application=doc.application,
                    action_taken=f"[{actor_str}] {doc.document_type} verified for application #NP-{doc.application.application_id:04d}"[:255]
                )
            except Exception:
                pass

        return Response({
            "message": f"{doc.document_type} marked as Verified.",
            "document_id": doc.document_id,
            "verification_status": doc.verification_status,
            "is_inspected": doc.is_inspected,
            "application_status": application_status,
            "application_verified": application_review_complete,
            "all_current_documents_verified": application_review_complete,
            "payment_unlocked": payment_unlocked,
            "queue_token": None,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject-document')
    def reject_document(self, request, pk=None):
        """Staff/Admin rejection of a specific document"""
        user = request.user
        user_type = getattr(user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can reject documents."}, status=status.HTTP_403_FORBIDDEN)

        reason = (request.data.get('reason') or request.data.get('remarks') or '').strip()
        if not reason:
            return Response({
                "error": "A rejection reason is required so the applicant can correct the issue."
            }, status=status.HTTP_400_BAD_REQUEST)

        document_snapshot = self.get_object()
        document_id = document_snapshot.document_id
        with transaction.atomic():
            application = Application.objects.select_for_update().get(
                application_id=document_snapshot.application_id
            )
            doc = Document.objects.select_for_update().select_related(
                'application',
                'application__applicant',
            ).get(document_id=document_id)

            app_id_req = request.data.get('application_id') or request.data.get('application')
            if app_id_req and str(doc.application_id) != str(app_id_req):
                return Response(
                    {"error": "Document does not belong to the requested application."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment_is_verified = application.payments.filter(
                Q(status='VERIFIED') | Q(payment_status='Completed')
            ).exists()
            if not payment_is_verified:
                return Response(
                    {"error": "Payment must be verified before staff can decide a document."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if doc.verification_status != 'Pending':
                return Response({
                    "error": (
                        f"This document already has a final {doc.verification_status} decision and cannot be rejected."
                    ),
                    "document_id": doc.document_id,
                    "current_status": doc.verification_status,
                }, status=status.HTTP_400_BAD_REQUEST)

            doc.verification_status = 'Rejected'
            doc.rejection_reason = reason
            doc.save(update_fields=['verification_status', 'rejection_reason'])

            application.status = 'Rejected'
            application.processing_notes = f'{doc.document_type} rejected: {reason}'
            application.last_updated = timezone.now()
            application.save(update_fields=['status', 'processing_notes', 'last_updated'])

            user_id = getattr(user, 'user_id', None)
            actor_staff = Staff.objects.filter(staff_id=user_id).first() if user_type == 'staff' else None
            actor_admin = Administrator.objects.filter(admin_id=user_id).first() if user_type == 'administrator' else None
            actor_str = f"Staff #{actor_staff.staff_id}" if actor_staff else (f"Admin #{actor_admin.admin_id}" if actor_admin else "Officer")
            try:
                ActivityLog.objects.create(
                    administrator=actor_admin,
                    application=doc.application,
                    action_taken=f"[{actor_str}] {doc.document_type} rejected: {reason}"[:255]
                )
            except Exception:
                pass

            if doc.application and doc.application.applicant:
                try:
                    Notification.objects.create(
                        applicant=doc.application.applicant,
                        application=doc.application,
                        type='Document Rejected',
                        message=f"Your {doc.document_type} was rejected: {reason}. Please upload a clearer/compliant copy.",
                        status='Unread'
                    )
                except Exception:
                    pass

        return Response({
            "message": f"{doc.document_type} rejected.",
            "document_id": doc.document_id,
            "verification_status": doc.verification_status,
            "rejection_reason": reason,
            "application_status": "Rejected",
        }, status=status.HTTP_200_OK)


class DigitalSignatureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DigitalSignature.objects.all().order_by('-signature_id')
    serializer_class = DigitalSignatureSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return DigitalSignature.objects.filter(application__applicant_id=user_id).order_by('-signature_id')
        return DigitalSignature.objects.all().order_by('-signature_id')

class QueueTokenViewSet(viewsets.ModelViewSet):
    queryset = QueueToken.objects.all().order_by('token_number')
    serializer_class = QueueTokenSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    VALID_STATUS_TRANSITIONS = {
        'Waiting': {'Called', 'Skipped'},
        'Called': {'Serving', 'Completed', 'Skipped'},
        'Serving': {'Completed', 'Skipped'},
        'Completed': set(),
        'Skipped': set(),
    }

    def get_permissions(self):
        if self.action in {'list', 'retrieve'}:
            return [IsAuthenticated()]
        return [IsStaffOrAdministrator()]

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "Queue tokens are assigned automatically after digital signature authorization."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "Queue token records are retained for audit history and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        queryset = QueueToken.objects.filter(
            application__digital_signature__is_valid=True
        )
        if user_type == 'applicant':
            return queryset.filter(application__applicant_id=user_id).order_by('-token_id')
        return queryset.order_by('token_number')

    @staticmethod
    def _validate_processing_gate(application):
        signature = getattr(application, 'digital_signature', None)
        is_paid = application.payments.filter(
            Q(status='VERIFIED') | Q(payment_status='Completed')
        ).exists()
        if not is_paid:
            raise ValidationError({'queue_status': 'Verified payment is required before processing.'})
        if not _current_document_review_is_complete(application):
            raise ValidationError({'queue_status': 'All current documents must be verified before processing.'})
        if application.biometric_status != 'Verified':
            raise ValidationError({'queue_status': 'Biometrics must be verified before processing.'})
        if not (signature and signature.is_valid):
            raise ValidationError({'queue_status': 'A valid digital signature is required before processing.'})

    def _validate_status_transition(self, current_status, new_status):
        valid_statuses = {choice[0] for choice in QueueToken.STATUS_CHOICES}
        if new_status not in valid_statuses:
            raise ValidationError({
                'queue_status': f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}"
            })
        if new_status == current_status:
            return
        if new_status not in self.VALID_STATUS_TRANSITIONS.get(current_status, set()):
            raise ValidationError({
                'queue_status': (
                    f"Queue token cannot change from {current_status} to {new_status}."
                )
            })

    def _apply_status(self, token, new_status):
        self._validate_status_transition(token.queue_status, new_status)
        if new_status == token.queue_status:
            return False

        self._validate_processing_gate(token.application)

        update_fields = ['queue_status']
        token.queue_status = new_status
        if new_status == 'Called' and not token.called_time:
            token.called_time = timezone.now()
            update_fields.append('called_time')

        user = self.request.user
        if getattr(user, 'user_type', None) == 'staff':
            staff = Staff.objects.filter(
                staff_id=getattr(user, 'user_id', None)
            ).first()
            if staff and token.staff_id != staff.staff_id:
                token.staff = staff
                update_fields.append('staff')
                if token.application and not token.application.staff_id:
                    token.application.staff = staff
                    token.application.save(update_fields=['staff', 'last_updated'])

        token.save(update_fields=update_fields)
        if new_status == 'Completed' and token.application:
            self._handle_token_completion(token)
        return True

    @transaction.atomic
    def perform_update(self, serializer):
        unexpected_fields = set(self.request.data.keys()) - {'queue_status'}
        if unexpected_fields:
            raise ValidationError({
                'error': 'Only queue_status can be changed through this endpoint.'
            })

        new_status = serializer.validated_data.get('queue_status')
        if not new_status:
            raise ValidationError({'queue_status': 'This field is required.'})

        token = QueueToken.objects.select_for_update().select_related(
            'application'
        ).get(pk=serializer.instance.pk)
        self._apply_status(token, new_status)
        serializer.instance = token

    def _handle_token_completion(self, token):
        app = token.application
        if app:
            self._validate_processing_gate(app)
            passport_number = assign_passport_number(app)
            if app.status not in {'Approved', 'Completed'}:
                app.status = 'Approved'
                app.processing_notes = (
                    'Queue processing completed. Passport generation is available.'
                )
                update_fields = ['status', 'processing_notes', 'last_updated']
                if not app.issue_date:
                    from django.conf import settings
                    validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
                    app.issue_date = timezone.localdate()
                    app.expiry_date = app.issue_date.replace(
                        year=app.issue_date.year + validity
                    )
                    update_fields.extend(['issue_date', 'expiry_date'])
                app.save(update_fields=update_fields)

            # The pre-queue signature is a v1 workflow authorization. Once a
            # number is allocated, replace it with a v2 signature that also
            # protects the final sequential passport number.
            try:
                _sign_application_record(app)
            except SigningConfigurationError as exc:
                raise ValidationError({
                    'queue_status': f'Passport number signing failed: {exc}'
                }) from exc
            if app.applicant:
                try:
                    Notification.objects.create(
                        applicant=app.applicant,
                        application=app,
                        type="Passport Ready",
                        message=(
                            f"Queue service for application #NP-{app.application_id:04d} is complete. "
                            f"Passport {passport_number} is approved and ready to generate or download."
                        ),
                        status="Unread"
                    )
                except Exception:
                    pass

    @action(detail=False, methods=['post'], url_path='call-next')
    def call_next(self, request):
        with transaction.atomic():
            token = QueueToken.objects.select_for_update(skip_locked=True).select_related(
                'application'
            ).filter(
                queue_status='Waiting',
                application__status='Pending',
                application__digital_signature__is_valid=True,
            ).order_by('token_date', 'token_number').first()
            if not token:
                return Response({"message": "No pending citizens in waiting queue.", "token": None}, status=status.HTTP_200_OK)

            self._validate_processing_gate(token.application)
            token.queue_status = 'Called'
            token.called_time = timezone.now()

            # If staff is calling, record staff assignment
            staff_id = getattr(request.user, 'user_id', None)
            if getattr(request.user, 'user_type', None) == 'staff' and staff_id:
                try:
                    token.staff = Staff.objects.get(staff_id=staff_id)
                    if token.application and not token.application.staff:
                        token.application.staff = token.staff
                        token.application.save(update_fields=['staff', 'last_updated'])
                except Staff.DoesNotExist:
                    pass

            token.save()
        serializer = self.get_serializer(token)
        return Response({"message": f"Token T-{token.token_number} called to Desk Counter.", "token": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='update-status')
    @transaction.atomic
    def update_status(self, request, pk=None):
        token_id = self.get_object().pk
        token = QueueToken.objects.select_for_update().select_related(
            'application'
        ).get(pk=token_id)
        new_status = request.data.get('queue_status')
        if not new_status:
            return Response(
                {'queue_status': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            self._apply_status(token, new_status)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(token)
        return Response({"message": f"Token status updated to {new_status}.", "token": serializer.data}, status=status.HTTP_200_OK)


def _build_system_report_payload(report_type):
    """Build an authoritative, JSON-safe snapshot directly from the database."""
    now = timezone.now()
    today = timezone.localdate()
    applications = Application.objects.all()
    queue_tokens = QueueToken.objects.all()
    documents = Document.objects.all()
    staff = Staff.objects.all()
    verified_payments = Payment.objects.filter(
        Q(status='VERIFIED') | Q(payment_status='Completed')
    )

    return {
        'report_type': report_type,
        'snapshot_date': today.isoformat(),
        'generated_at': now.isoformat(),
        'total_applications': applications.count(),
        'applications_submitted_today': applications.filter(
            submission_date__date=today
        ).count(),
        'pending_applications': applications.filter(status='Pending').count(),
        'under_review_applications': applications.filter(status='Under Review').count(),
        'approved_applications': applications.filter(status='Approved').count(),
        'rejected_applications': applications.filter(status='Rejected').count(),
        'completed_applications': applications.filter(status='Completed').count(),
        'total_queue_tokens': queue_tokens.count(),
        'queue_tokens_today': queue_tokens.filter(token_date=today).count(),
        'waiting_tokens': queue_tokens.filter(queue_status='Waiting').count(),
        'called_tokens': queue_tokens.filter(queue_status='Called').count(),
        'serving_tokens': queue_tokens.filter(queue_status='Serving').count(),
        'completed_tokens': queue_tokens.filter(queue_status='Completed').count(),
        'total_documents': documents.count(),
        'pending_documents': documents.filter(verification_status='Pending').count(),
        'verified_documents': documents.filter(verification_status='Verified').count(),
        'rejected_documents': documents.filter(verification_status='Rejected').count(),
        'total_staff': staff.count(),
        'active_staff': staff.filter(is_active=True, status='Active').count(),
        'verified_payments': verified_payments.count(),
        'verified_revenue_npr': float(
            verified_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        ),
        'issued_passports': DigitalSignature.objects.filter(is_valid=True).count(),
    }


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-report_id')
    serializer_class = ReportSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]

    def perform_create(self, serializer):
        report_type = serializer.validated_data['report_type']
        serializer.save(
            administrator_id=getattr(self.request.user, 'user_id', None),
            data_payload=_build_system_report_payload(report_type),
        )


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all().order_by('-log_id')
    serializer_class = ActivityLogSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-notification_id')
    serializer_class = NotificationSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return Notification.objects.filter(applicant_id=user_id).order_by('-notification_id')
        return Notification.objects.all().order_by('-notification_id')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        if getattr(request.user, 'user_type', None) != 'applicant':
            return Response(
                {"error": "Only citizens can update citizen notifications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_id = getattr(request.user, 'user_id', None)
        if user_id:
            Notification.objects.filter(applicant_id=user_id, status='Unread').update(status='Read')
        return Response({"message": "All notifications marked as read."}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "Notifications are created only by system workflows."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def perform_update(self, serializer):
        if getattr(self.request.user, 'user_type', None) != 'applicant':
            raise PermissionDenied("Only citizens can update citizen notifications.")
        unexpected = set(self.request.data) - {'status'}
        if unexpected or self.request.data.get('status') != 'Read':
            raise ValidationError({
                'status': 'Notifications may only be marked as Read.'
            })
        serializer.save(status='Read')


from .payment_service import PaymentService


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_id')
    serializer_class = PaymentSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "Use the signed eSewa payment request endpoint to initiate a payment."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"error": "Payment records can only be updated by verified gateway responses."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "Payment records are retained for audit history and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        qs = Payment.objects.all().select_related('application', 'applicant').order_by('-payment_id')
        if user_type == 'applicant':
            qs = qs.filter(applicant_id=user_id)

        # Optional filters for Admin/Staff or query
        app_id = self.request.query_params.get('application_id')
        if app_id:
            try:
                app_id = int(app_id)
                if app_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({
                    'application_id': 'A valid positive application ID is required.'
                })
            qs = qs.filter(application_id=app_id)

        status_param = self.request.query_params.get('status')
        if status_param and status_param != 'All':
            qs = qs.filter(status__iexact=status_param)

        search_query = self.request.query_params.get('search')
        if search_query:
            qs = qs.filter(
                Q(payment_reference__icontains=search_query) |
                Q(transaction_id__icontains=search_query) |
                Q(applicant__full_name__icontains=search_query)
            )

        return qs

    @action(detail=False, methods=['post'], url_path='create-request')
    def create_payment_request(self, request):
        """
        Initiates a signed eSewa ePay v2 request for an application.
        The backend authoritatively calculates the fee and signs all gateway fields.
        """
        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        app_id = request.data.get('application_id')
        payment_type = request.data.get('payment_type', 'APPLICATION_FEE')
        gateway_name = request.data.get('gateway_name', 'eSewa')

        if not str(gateway_name).lower().startswith('esewa'):
            return Response(
                {"error": "Only eSewa ePay is currently available for online payments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        gateway_name = 'eSewa'

        if not app_id:
            return Response(
                {"error": "application_id is required to generate payment request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        application = Application.objects.filter(application_id=app_id).first()
        if not application:
            return Response(
                {"error": f"Application #{app_id} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Enforce applicant access control
        if user_type == 'applicant' and application.applicant_id != user_id:
            return Response(
                {"error": "Unauthorized. You may only initiate payments for your own applications."},
                status=status.HTTP_403_FORBIDDEN
            )

        already_verified = application.payments.filter(
            Q(status='VERIFIED') | Q(payment_status='Completed')
        ).exists()
        if not already_verified:
            try:
                PaymentService.validate_documents_ready_for_payment(application)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # RULE 7: Validate amount if explicitly sent by client
        client_amount = request.data.get('amount')
        expected_fee = application.fee_amount
        if client_amount is not None:
            try:
                client_dec = Decimal(str(client_amount))
                if client_dec != Decimal(str(expected_fee)):
                    return Response({
                        "error": f"Incorrect payment amount: NPR {client_dec:,.2f}. The selected package '{application.passport_category}' requires NPR {expected_fee:,.2f}.",
                        "expected_amount": float(expected_fee),
                        "submitted_amount": float(client_dec)
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({"error": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

        applicant = application.applicant
        try:
            payment = PaymentService.create_payment_request(
                application=application,
                applicant=applicant,
                payment_type=payment_type,
                gateway_name=gateway_name
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        form_fields = {}
        payment_url = None
        if payment.status != 'VERIFIED':
            success_url = request.build_absolute_uri('/api/payments/esewa/success/')
            failure_base_url = request.build_absolute_uri('/api/payments/esewa/failure/')
            failure_url = f"{failure_base_url}?{urlencode({'reference': payment.payment_reference})}"
            try:
                form_fields = PaymentService.build_esewa_payment_form(
                    payment=payment,
                    success_url=success_url,
                    failure_url=failure_url,
                )
            except ValueError as exc:
                return Response(
                    {"error": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            payment_url = PaymentService.GATEWAY_URL
            payment.qr_payload = json.dumps(form_fields, separators=(',', ':'))
            payment.remarks = 'Signed eSewa ePay v2 form generated'
            payment.save(update_fields=['qr_payload', 'remarks', 'updated_at'])

        return Response({
            "message": "Payment request initiated successfully.",
            "payment_id": payment.payment_id,
            "payment_reference": payment.payment_reference,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_type": payment.payment_type,
            "status": payment.status,
            "gateway_name": payment.gateway_name,
            "payment_url": payment_url,
            "form_fields": form_fields,
            "already_paid": payment.status == 'VERIFIED',
            "qr_code": payment.qr_code,
            "qr_payload": payment.qr_payload,
            "transaction_id": payment.transaction_id,
            "application_id": application.application_id,
            "applicant_name": applicant.full_name if applicant else "Citizen",
            "environment": PaymentService.ENVIRONMENT,
            # Passport package details — read from Application model properties
            "passport_category": application.passport_category or "Ordinary (34 Pages)",
            "passport_type": application.passport_type,
            "passport_pages": application.passport_pages,
            "delivery_type": application.delivery_type,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path=r'status/(?P<reference>[\w\-]+)')
    def status_by_reference(self, request, reference=None):
        """
        Sanitized payment status endpoint used by the applicant portal.
        Does not expose gateway secrets or internal hashes.
        """
        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        payment = Payment.objects.filter(payment_reference=reference).select_related('application', 'applicant').first()
        if not payment:
            return Response(
                {"error": f"No payment request found matching reference '{reference}'."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Access check for applicants
        if user_type == 'applicant' and payment.applicant_id != user_id:
            return Response(
                {"error": "Unauthorized to inspect payment belonging to another citizen."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh_requested = str(request.query_params.get('refresh', '')).lower() in {'1', 'true', 'yes'}
        if (
            refresh_requested
            and payment.gateway_name == 'eSewa'
            and payment.status in {'PAID', 'PAYMENT_INITIATED'}
        ):
            PaymentService.verify_esewa_transaction(payment)
            payment.refresh_from_db()

        return Response({
            "payment_reference": payment.payment_reference,
            "application_id": payment.application_id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_type": payment.payment_type,
            "gateway_name": payment.gateway_name,
            "status": payment.status,
            "is_verified": payment.status == "VERIFIED",
            "transaction_id": payment.transaction_id,
            "created_at": payment.created_at,
            "paid_at": payment.paid_at,
            "verified_at": payment.verified_at,
            "failure_reason": payment.failure_reason,
            "steps": payment.application.get_workflow_steps() if payment.application else []
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_esewa_payment(self, request):
        """Record that the citizen is leaving the portal for the eSewa checkout."""
        reference = request.data.get('payment_reference')
        payment = Payment.objects.filter(payment_reference=reference).first()
        if not payment:
            return Response(
                {"error": "Payment reference was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        if (
            getattr(user, 'user_type', None) == 'applicant'
            and payment.applicant_id != getattr(user, 'user_id', None)
        ):
            return Response(
                {"error": "Unauthorized to initiate this payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if payment.status != 'VERIFIED':
            try:
                PaymentService.validate_documents_ready_for_payment(payment.application)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if payment.status in {'PENDING', 'QR_GENERATED'}:
            payment.status = 'PAYMENT_INITIATED'
            payment.failure_reason = None
            payment.remarks = 'Citizen redirected to eSewa checkout'
            payment.save()
        elif payment.status not in {'PAYMENT_INITIATED', 'PAID', 'VERIFIED'}:
            return Response(
                {"error": f"Payment cannot be initiated from status {payment.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "payment_reference": payment.payment_reference,
            "status": payment.status,
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='esewa/success',
        url_name='esewa-success',
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def esewa_success(self, request):
        """Handle eSewa's signed browser return and send the citizen back to the portal."""
        success, message, payment = PaymentService.process_esewa_success(
            request.query_params.get('data', '')
        )
        if success:
            result = 'success'
        elif payment and payment.status in {'PAID', 'PAYMENT_INITIATED'}:
            result = 'pending'
        else:
            result = 'failure'

        query = {'payment': result}
        if payment:
            query['reference'] = payment.payment_reference
        if result == 'pending':
            query['reason'] = 'verification_pending'
        return redirect(f"/applicant/apply/?{urlencode(query)}")

    @action(
        detail=False,
        methods=['get'],
        url_path='esewa/failure',
        url_name='esewa-failure',
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def esewa_failure(self, request):
        """Handle eSewa failure/pending redirects without trusting unsigned state."""
        query = {'payment': 'failure'}
        reference = request.query_params.get('reference')
        if reference:
            query['reference'] = reference
        return redirect(f"/applicant/apply/?{urlencode(query)}")

    @action(detail=False, methods=['post'], url_path='webhook', authentication_classes=[], permission_classes=[])
    def webhook(self, request):
        """
        Idempotent payment gateway webhook endpoint.
        Verifies signatures, validates amounts, and records verified transactions.
        """
        payload = request.data
        signature = request.headers.get('X-Gateway-Signature') or payload.get('signature')

        success, msg, payment = PaymentService.process_webhook(payload, signature=signature)
        if not success:
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": msg,
            "payment_reference": payment.payment_reference if payment else None,
            "status": payment.status if payment else "UNKNOWN",
            "transaction_id": payment.transaction_id if payment else None
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='simulate-sandbox-callback')
    def simulate_sandbox_callback(self, request):
        """
        Sandbox development testing tool.
        Triggers a simulated, signed gateway webhook callback for a payment reference.
        Clearly flagged: DEVELOPMENT/SANDBOX PAYMENT ≠ REAL PRODUCTION PAYMENT.
        """
        if PaymentService.ENVIRONMENT == 'production':
            return Response(
                {"error": "Payment simulation is disabled in production."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reference = request.data.get('payment_reference')
        if not reference:
            return Response({"error": "payment_reference is required for simulation."}, status=status.HTTP_400_BAD_REQUEST)

        payment_record = Payment.objects.filter(
            payment_reference=reference
        ).only('applicant_id').first()
        if not payment_record:
            return Response(
                {"error": "Payment reference was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if (
            getattr(request.user, 'user_type', None) == 'applicant'
            and payment_record.applicant_id != getattr(request.user, 'user_id', None)
        ):
            return Response(
                {"error": "Unauthorized to simulate payment for another citizen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, msg, payment = PaymentService.simulate_sandbox_payment(reference)
        if not success:
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": msg,
            "environment_notice": "DEVELOPMENT/SANDBOX PAYMENT ≠ REAL PRODUCTION PAYMENT",
            "payment_reference": payment.payment_reference,
            "status": payment.status,
            "transaction_id": payment.transaction_id,
            "paid_at": payment.paid_at,
            "verified_at": payment.verified_at
        }, status=status.HTTP_200_OK)
    # Action aliases for testing/backward compatibility
    def create_request(self, request, *args, **kwargs):
        return self.create_payment_request(request, *args, **kwargs)

    def status_by_ref(self, request, *args, **kwargs):
        return self.status_by_reference(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    identifier = (request.data.get('email') or request.data.get('username') or '').strip()
    password = request.data.get('password')
    requested_portal = str(request.data.get('portal_role') or '').strip().lower()
    requested_portal = {
        'applicant': 'citizen',
        'admin': 'administrator',
    }.get(requested_portal, requested_portal)
    remember_me = _as_bool(request.data.get('remember_me', False))

    if requested_portal and requested_portal not in ('citizen', 'staff', 'administrator'):
        return Response(
            {
                "error": "The selected sign-in portal is invalid.",
                "code": "invalid_portal",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not identifier or not password:
        return Response(
            {
                "error": "Email/username and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    retry_after = lockout_seconds(request, identifier)
    if retry_after:
        response = Response(
            {
                "error": "Too many login attempts. Please try again later.",
                "retry_after_seconds": retry_after,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        response['Retry-After'] = str(retry_after)
        return response

    administrator = Administrator.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()
    staff = Staff.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()
    applicant = Applicant.objects.filter(email__iexact=identifier).first()

    authenticated = None
    for user_type, user in (
        ('administrator', administrator),
        ('staff', staff),
        ('applicant', applicant),
    ):
        if user and check_password(password, user.password):
            authenticated = (user_type, user)
            break

    if authenticated is None:
        # Perform a password hash comparison even for unknown identifiers to
        # reduce account-enumeration timing differences.
        if not any((administrator, staff, applicant)):
            check_password(password, make_password('invalid-login-placeholder'))
        record_login_failure(request, identifier)
        retry_after = lockout_seconds(request, identifier)
        if retry_after:
            response = Response(
                {
                    "error": "Too many login attempts. Please try again later.",
                    "retry_after_seconds": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response['Retry-After'] = str(retry_after)
            return response
        return Response(
            {"error": "Invalid email/username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user_type, authenticated_user = authenticated
    clear_login_failures(request, identifier)

    authenticated_portal = 'citizen' if user_type == 'applicant' else user_type
    if requested_portal and requested_portal != authenticated_portal:
        return Response(
            {
                "error": "These credentials do not belong to the selected portal.",
                "code": "wrong_portal",
                "correct_portal": authenticated_portal,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if not _personnel_account_is_active(user_type, authenticated_user):
        return Response(
            {"error": "This personnel account is inactive or deactivated."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if user_type in {'administrator', 'staff'} and settings.PERSONNEL_MFA_REQUIRED:
        return _start_personnel_mfa(user_type, authenticated_user, remember_me)

    if user_type == 'administrator':
        ActivityLog.objects.create(
            administrator=authenticated_user,
            action_taken=f"Administrator logged in: {authenticated_user.full_name} ({authenticated_user.username or authenticated_user.email})",
        )

    if user_type in {'administrator', 'staff', 'applicant'}:
        return _issue_login_response(user_type, authenticated_user, remember_me)

    return Response({"error": "Authentication failed."}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_login_mfa(request):
    challenge_id = str(request.data.get('challenge_id') or '').strip()
    otp = str(request.data.get('code') or '').strip()
    if not challenge_id or not re.fullmatch(r'\d{6}', otp):
        return Response(
            {'error': 'A valid verification challenge and six-digit code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        try:
            session_row = Session.objects.select_for_update().get(
                session_key=challenge_id,
                expire_date__gt=timezone.now(),
            )
        except Session.DoesNotExist:
            return Response(
                {'error': 'This verification challenge is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = session_row.get_decoded()
        if data.get('challenge_kind') != 'personnel_mfa':
            return Response(
                {'error': 'This verification challenge is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempts = int(data.get('attempts', 0))
        if attempts >= settings.PERSONNEL_MFA_MAX_ATTEMPTS:
            session_row.delete()
            return Response(
                {'error': 'Too many incorrect verification attempts. Sign in again.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not check_password(otp, data.get('otp_hash', '')):
            attempts += 1
            if attempts >= settings.PERSONNEL_MFA_MAX_ATTEMPTS:
                session_row.delete()
            else:
                data['attempts'] = attempts
                session_row.session_data = SessionStore().encode(data)
                session_row.save(update_fields=['session_data'])
            return Response(
                {'error': 'The verification code is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_type = data.get('user_type')
        user_id = data.get('user_id')
        remember_me = bool(data.get('remember_me'))
        model = {'administrator': Administrator, 'staff': Staff}.get(user_type)
        try:
            user = model.objects.get(pk=user_id) if model else None
        except (Administrator.DoesNotExist, Staff.DoesNotExist):
            user = None
        session_row.delete()

        if user is None or not _personnel_account_is_active(user_type, user):
            return Response(
                {'error': 'This personnel account is no longer active.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_type == 'administrator':
            ActivityLog.objects.create(
                administrator=user,
                action_taken=f"Administrator completed MFA sign-in: {user.full_name} ({user.username or user.email})",
            )
        return _issue_login_response(user_type, user, remember_me)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    session = getattr(request, 'auth', None)
    if isinstance(session, AuthToken):
        session.revoke()
    response = Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
    response.delete_cookie(
        settings.AUTH_TOKEN_COOKIE_NAME,
        path='/',
        samesite=settings.AUTH_TOKEN_COOKIE_SAMESITE,
    )
    return response


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_signature_view(request, verification_code):
    try:
        signature = DigitalSignature.objects.select_related(
            'application', 'application__applicant'
        ).get(verification_code=verification_code)
    except DigitalSignature.DoesNotExist:
        return Response({"valid": False, "error": "Signature not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        valid = verify_signature(signature)
    except SigningConfigurationError:
        return Response(
            {"valid": False, "error": "Signature verification service is unavailable."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        "valid": valid,
        "application_reference": f"NP-{signature.application_id:04d}",
        "passport_number": signature.application.passport_number,
        "certificate_serial": signature.certificate_serial,
        "algorithm": signature.algorithm,
        "key_id": signature.key_id,
        "signing_authority": signature.signing_authority,
        "signed_at": signature.signed_at,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_view(request):
    role = str(request.data.get('role', 'citizen')).lower()

    # Enforce that Staff and Administrator accounts cannot be registered publicly
    if role in ('staff', 'administrator'):
        return Response(
            {
                "role": ["Staff and Administrator accounts cannot be registered publicly. Only an authorized Administrator can provision personnel."]
            },
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CitizenRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated = serializer.validated_data
    first_name = validated['first_name']
    middle_name = validated.get('middle_name', '')
    last_name = validated['last_name']
    fields = {
        'full_name': ' '.join(part for part in (first_name, middle_name, last_name) if part),
        'email': validated['email'],
        'phone': validated['phone'],
        'password': validated['password'],
        'date_of_birth': validated['date_of_birth'],
        'gender': validated['gender'],
        'nationality': validated['nationality'],
        'address': validated['address'],
    }

    try:
        with transaction.atomic():
            user = Applicant.objects.create(**fields)
    except IntegrityError as error:
        err_msg = str(error)
        if 'phone' in err_msg.lower():
            return Response(
                {'phone': ['This phone number is already registered. Please use another phone number or log in to your existing account.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'email' in err_msg.lower():
            return Response(
                {'email': ['This email address is already registered. Please use another email or log in.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'non_field_errors': ['Registration could not be completed due to a data conflict.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception('Unexpected citizen registration failure.')
        return Response(
            {'non_field_errors': ['Registration could not be completed. Please try again later.']},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({
        'message': 'Registration successful. You can now log in.',
        'role': 'citizen',
        'user_id': user.applicant_id,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([PublicTrackingThrottle])
def track_application_view(request):
    """
    Track with an unguessable reference plus the applicant's date of birth.
    Sequential database and queue identifiers are deliberately not accepted.
    """
    query = request.query_params.get('reference') or request.query_params.get('query')
    date_of_birth = str(request.query_params.get('date_of_birth') or '').strip()
    if not query or not date_of_birth:
        return Response(
            {"error": "Tracking reference and date of birth are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        import uuid
        normalized_reference = uuid.UUID(str(query).strip())
        from datetime import date
        normalized_birth_date = date.fromisoformat(date_of_birth)
    except (ValueError, TypeError):
        return Response(
            {"error": "Enter a valid tracking reference and date of birth."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    application = Application.objects.select_related('applicant').filter(
        tracking_reference=normalized_reference,
        applicant__date_of_birth=normalized_birth_date,
    ).first()
    if application is None:
        return Response(
            {"error": "No application matches those tracking details."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Mask applicant name for privacy (e.g., "Ram Sharma" -> "R** S*****")
    def mask_name(name):
        if not name:
            return "Citizen"
        parts = name.split()
        masked = []
        for p in parts:
            if len(p) > 1:
                masked.append(p[0] + '*' * (len(p) - 1))
            else:
                masked.append(p)
        return ' '.join(masked)

    facts = build_workflow_facts(application)
    signature_verified = facts['signature_is_valid']
    payment_verified = facts['payment_verified']

    # A queue token belongs to the public workflow only after signing.
    token_data = None
    if signature_verified and facts['queue_token']:
        token = facts['queue_token']
        token_data = {
            "token_number": token.token_number,
            "queue_status": token.queue_status,
            "token_date": str(token.token_date),
            "time_slot": str(token.time_slot) if token.time_slot else None,
            "called_time": str(token.called_time) if token.called_time else None,
        }

    # Current document versions only; rejected historical versions remain stored.
    docs = facts['documents']
    total_docs = len(docs)
    verified_docs = len(facts['verified_documents'])
    rejected_docs = len(facts['rejected_documents'])
    has_photo = bool(facts['photo'])
    has_identity = facts['has_identity']
    documents_uploaded = bool(docs and has_photo and has_identity and not rejected_docs)
    documents_verified = facts['documents_complete']
    queue_completed = facts['queue_complete']

    if not documents_uploaded:
        current_step = 'documents'
    elif not payment_verified:
        current_step = 'fee'
    elif not documents_verified:
        current_step = 'verification'
    elif application.biometric_status != 'Verified':
        current_step = 'biometrics'
    elif not signature_verified:
        current_step = 'signature'
    elif not queue_completed:
        current_step = 'queue'
    else:
        current_step = 'passport_ready'

    response_data = {
        "application_id": application.application_id,
        "applicant_name": mask_name(application.applicant.full_name if application.applicant else None),
        "submission_date": application.submission_date,
        "status": application.status,
        "passport_category": getattr(application, 'passport_category', 'Ordinary (34 Pages)'),
        "biometric_status": getattr(application, 'biometric_status', 'Pending'),
        "last_updated": application.last_updated,
        "documents_count": total_docs,
        "documents_verified": verified_docs,
        "documents_rejected": rejected_docs,
        "payment_verified": payment_verified,
        "signature_verified": signature_verified,
        "current_step": current_step,
        "queue_token": token_data,
    }

    return Response(response_data, status=status.HTTP_200_OK)
