from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError
from django.db.models import Q, Max
from django.utils import timezone
from django.http import HttpResponse
import os
import re
import secrets
import hashlib
import time
from .models import AuthToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from .authentication import CustomTokenAuthentication
from .pdf_generator import generate_passport_pdf

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


# 1. APPLICANT API

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all().order_by('-applicant_id')
    serializer_class = ApplicantSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [
        IsApplicant | IsStaffOrAdministrator
    ]

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
        return super().destroy(request, *args, **kwargs)


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
        return Administrator.objects.first()

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
        if not new_password or len(new_password) < 6:
            return Response(
                {"error": "New password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST
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

        if applicant_id_to_check:
            existing_apps = Application.objects.filter(applicant_id=applicant_id_to_check)

            # CASE 2, 3, 4: Reject if any application is currently active (Pending, Under Review, Approved)
            active_app = existing_apps.filter(status__in=['Pending', 'Under Review', 'Approved']).first()
            if active_app:
                raise ValidationError({
                    "error": "You already have a passport application.",
                    "detail": f"You cannot submit another application. Active application #NP-{active_app.application_id:04d} is currently '{active_app.status}'.",
                    "application_id": active_app.application_id,
                    "status": active_app.status
                })

            # CASE 5: Check issued/completed passports
            completed_passports = existing_apps.filter(status='Completed').order_by('-application_id')
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
                    # CASE 7: Reject if another renewal is already active
                    active_renewal = existing_apps.filter(
                        application_type='RENEWAL',
                        status__in=['Pending', 'Under Review', 'Approved']
                    ).first()
                    if active_renewal:
                        raise ValidationError({
                            "error": "You already have a renewal application.",
                            "detail": f"Active renewal application #NP-{active_renewal.application_id:04d} is already in progress with status '{active_renewal.status}'.",
                            "application_id": active_renewal.application_id,
                            "status": active_renewal.status
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

        if user_type == 'applicant' and not serializer.validated_data.get('applicant'):
            app = serializer.save(
                applicant_id=user_id,
                passport_category=category,
                service_type=service_type,
                application_type=app_type,
                biometric_status='Pending'
            )
        else:
            app = serializer.save(
                passport_category=category,
                service_type=service_type,
                application_type=app_type,
                biometric_status='Pending'
            )


        # 1. Automatically provision a real QueueToken in PostgreSQL for this application
        if not hasattr(app, 'queue_token') or not QueueToken.objects.filter(application=app).exists():
            today = timezone.localdate()
            max_token = QueueToken.objects.filter(token_date=today).aggregate(Max('token_number'))['token_number__max']
            next_token_num = (max_token + 1) if max_token else 101
            QueueToken.objects.create(
                application=app,
                token_number=next_token_num,
                queue_status='Waiting'
            )

        # 2. Provision initial fee assessment record in Payment table
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

        # 3. Provision initial confirmation Notification for applicant
        applicant_inst = getattr(app, 'applicant', None)
        if applicant_inst:
            Notification.objects.create(
                applicant=applicant_inst,
                application=app,
                type='Application Submitted',
                message=f"Application #NP-{app.application_id:04d} ({category}) submitted successfully and enrolled in the digital review queue.",
                status='Unread'
            )

    def perform_update(self, serializer):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        instance = self.get_object()

        # If applicant, reject changes to official status fields or submitted package fields (RULE 9)
        if user_type == 'applicant':
            restricted_fields = ['status', 'staff', 'biometric_status', 'processing_notes', 'passport_category', 'service_type']
            for field in restricted_fields:
                if field in self.request.data:
                    new_val = self.request.data.get(field)
                    old_val = getattr(instance, field, None)
                    if hasattr(old_val, 'staff_id'):
                        old_val = old_val.staff_id
                    if str(new_val) != str(old_val) and new_val is not None:
                        raise PermissionDenied(f"Applicants are not authorized to modify field '{field}' after submission.")

        # Check approval rule: CANNOT transition to 'Approved' unless all required documents exist and are verified!
        target_status = self.request.data.get('status') or serializer.validated_data.get('status')
        if target_status == 'Approved' and instance.status != 'Approved':
            docs = instance.documents.all()
            if not docs.exists():
                raise ValidationError({
                    "status": "Cannot approve application: No required documents have been uploaded."
                })

            # 1. Passport photo must exist and be verified
            has_verified_photo = docs.filter(document_type='Passport Photo', verification_status='Verified').exists()
            if not has_verified_photo:
                raise ValidationError({
                    "status": "Cannot approve application: A verified Passport Photo is mandatory."
                })

            # 2. Primary identity document must exist and be verified (Citizenship or National ID)
            has_verified_id = docs.filter(
                Q(document_type__icontains='Citizenship') | Q(document_type__icontains='National ID') | Q(document_type__icontains='NID'),
                verification_status='Verified'
            ).exists()
            if not has_verified_id:
                raise ValidationError({
                    "status": "Cannot approve application: A verified Citizenship Certificate or National ID (NID) is required."
                })

            # 3. No document can be Pending or Rejected
            unverified_docs = docs.exclude(verification_status='Verified')
            if unverified_docs.exists():
                unresolved = [f"{d.document_type} ({d.verification_status})" for d in unverified_docs]
                raise ValidationError({
                    "status": f"Cannot approve application: All documents must be verified. Unresolved documents: {', '.join(unresolved)}."
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

    @action(detail=True, methods=['get'], url_path='workflow-status')
    def workflow_status(self, request, pk=None):
        """
        Returns the granular 9-step workflow state for a specific application.
        """
        app = self.get_object()
        sig = getattr(app, 'digital_signature', None)
        can_download = (app.status in ['Approved', 'Completed']) and bool(sig and sig.is_valid)

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
            "can_download_pdf": can_download,
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

                # Document summary and photo inspection
                docs = list(latest_app.documents.all()) if hasattr(latest_app, 'documents') else []
                total_docs = len(docs)
                verified_docs = sum(1 for d in docs if d.verification_status == 'Verified')
                rejected_docs_count = sum(1 for d in docs if d.verification_status == 'Rejected')
                pending_docs = sum(1 for d in docs if d.verification_status == 'Pending')

                photo_doc = next((d for d in docs if 'photo' in (d.document_type or '').lower()), None)
                has_photo = bool(photo_doc)
                photo_verified = bool(photo_doc and photo_doc.verification_status == 'Verified')
                photo_rejected = bool(photo_doc and photo_doc.verification_status == 'Rejected')

                # Active payment info — STRICT PAYMENT GATE (backend source of truth)
                payment_reference = None
                payment_status_val = None
                is_payment_verified = False
                try:
                    from django.db.models import Q
                    active_pay = latest_app.payments.order_by('-payment_id').first()
                    if active_pay:
                        payment_reference = active_pay.payment_reference
                        payment_status_val = active_pay.status
                    v_pay = latest_app.payments.filter(Q(status='VERIFIED') | Q(payment_status='Completed')).first()
                    if v_pay:
                        is_payment_verified = True
                except Exception:
                    pass

                sig = getattr(latest_app, 'digital_signature', None)
                is_sig_valid = bool(sig and sig.is_valid)

                # STRICT ISSUANCE GATE: Can download PDF only when Approved/Completed, payment verified, digital signature valid, and photo verified
                can_download = bool(
                    (latest_app.status in ['Approved', 'Completed']) and
                    is_payment_verified and
                    is_sig_valid and
                    photo_verified
                )

                # Queue token info
                queue_token_info = None
                try:
                    qt = getattr(latest_app, 'queue_token', None)
                    if qt:
                        queue_token_info = {
                            'token_id': qt.token_id,
                            'token_number': qt.token_number,
                            'queue_status': qt.queue_status,
                            'token_date': str(qt.token_date) if qt.token_date else None,
                        }
                except Exception:
                    pass

                doc_summary = {
                    'total': total_docs,
                    'verified': verified_docs,
                    'rejected': rejected_docs_count,
                    'pending': pending_docs,
                    'has_photo': has_photo,
                    'photo_verified': photo_verified,
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
                is_docs_verified = (total_docs > 0 and pending_docs == 0 and rejected_docs_count == 0 and verified_docs == total_docs and photo_verified)
                is_approved_or_verified = is_approved or is_completed or is_docs_verified

                if total_docs == 0 or rejected_docs_count > 0 or not has_photo or photo_rejected:
                    current_step_key = 'documents'
                elif not is_approved_or_verified or not photo_verified:
                    current_step_key = 'verification'
                elif not is_payment_verified:
                    current_step_key = 'fee'
                elif not is_sig_valid:
                    current_step_key = 'signature'
                elif not queue_token_info:
                    current_step_key = 'queue'
                else:
                    current_step_key = 'passport_ready'

                photo_url = None
                if photo_doc and photo_doc.file_path:
                    try:
                        photo_url = photo_doc.file_path.url
                    except Exception:
                        photo_url = None

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
                {"step": 1, "key": "registration", "title": "Online Registration", "status": "Completed", "details": f"Registered citizen: {citizen_name}", "action_url": "/applicant/profile/", "action_label": "View Profile"},
                {"step": 2, "key": "application", "title": "Fill Application", "status": "Action Required", "details": "Please complete your passport application form", "action_url": "/applicant/apply/", "action_label": "Start Application"},
                {"step": 3, "key": "documents", "title": "Upload Documents", "status": "Not Started", "details": "Upload Citizenship and proofs after submitting application", "action_url": "/applicant/documents/", "action_label": "Upload Documents"},
                {"step": 4, "key": "queue", "title": "Queue Token Generation", "status": "Not Started", "details": "Token is generated upon application submission", "action_url": "/applicant/queue/", "action_label": "Queue Info"},
                {"step": 5, "key": "fee", "title": "Fee Assessment", "status": "Not Started", "details": "Assessed upon passport category selection", "action_url": "/applicant/apply/", "action_label": "Tariff Details"},
                {"step": 6, "key": "biometrics", "title": "Digital Biometrics Match", "status": "Not Started", "details": "Digital authentication of credentials", "action_url": "/applicant/documents/", "action_label": "Biometrics"},
                {"step": 7, "key": "verification", "title": "Staff Verification", "status": "Not Started", "details": "Officer verification of credentials", "action_url": "/applicant/dashboard/", "action_label": "Track Review"},
                {"step": 8, "key": "signature", "title": "Government Digital Signature", "status": "Not Started", "details": "Issued upon officer verification", "action_url": "/applicant/dashboard/", "action_label": "Signature"},
                {"step": 9, "key": "passport_ready", "title": "Virtual Passport Ready", "status": "Not Started", "details": "Available once all stages are complete", "action_url": "/applicant/dashboard/", "action_label": "Virtual Passport", "can_download": False}
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
            {"step": 1, "key": "registration", "title": "Online Registration", "status": "Action Required", "details": "Create citizen account with valid details", "action_url": "/register/", "action_label": "Register Now"},
            {"step": 2, "key": "application", "title": "Fill Application", "status": "Not Started", "details": "Complete digital e-passport application", "action_url": "/login/", "action_label": "Sign In"},
            {"step": 3, "key": "documents", "title": "Upload Documents", "status": "Not Started", "details": "Upload Citizenship & photos", "action_url": "/login/", "action_label": "Sign In"},
            {"step": 4, "key": "queue", "title": "Queue Token Generation", "status": "Not Started", "details": "Automated digital queue token", "action_url": "/track/", "action_label": "Track Queue"},
            {"step": 5, "key": "fee", "title": "Fee Assessment", "status": "Not Started", "details": "Category tariffs (34/66 pages/Urgent)", "action_url": "/#services", "action_label": "View Tariffs"},
            {"step": 6, "key": "biometrics", "title": "Digital Biometrics Match", "status": "Not Started", "details": "System-level biometric verification", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 7, "key": "verification", "title": "Staff Verification", "status": "Not Started", "details": "Desk officer review & validation", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 8, "key": "signature", "title": "Government Digital Signature", "status": "Not Started", "details": "Certified digital signature", "action_url": "/#process", "action_label": "Learn More"},
            {"step": 9, "key": "passport_ready", "title": "Virtual Passport Ready", "status": "Not Started", "details": "Direct portal access & PDF download", "action_url": "/login/", "action_label": "Citizen Login", "can_download": False}
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

    @action(detail=True, methods=['get'], url_path='download-pdf', permission_classes=[AllowAny])
    def download_pdf(self, request, pk=None):
        """
        Generates and serves the official Virtual Passport PDF certificate.
        Strictly gated:
        1. Application exists and user authorized.
        2. Application status is Approved or Completed.
        3. Required documents (Citizenship & Passport Photo) are verified.
        4. Payment is verified by the backend (STRICT PAYMENT GATE).
        5. Government digital signature is authorized and valid.
        """
        app = self.get_object()

        # Permission check: applicant can download their own, staff/admin can download any
        user = getattr(request, 'user', None)
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        if user and getattr(user, 'is_authenticated', False) and user_type == 'applicant' and app.applicant_id != user_id:
            return Response({"error": "You are not authorized to download this passport."}, status=status.HTTP_403_FORBIDDEN)

        if app.status not in ['Approved', 'Completed']:
            return Response(
                {"error": f"Virtual Passport is not yet ready. Current application status is '{app.status}'. All previous stages must be completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Check required documents & verified passport-size photo
        docs = list(app.documents.all()) if hasattr(app, 'documents') else []
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

        unverified_docs = [d for d in docs if d.verification_status != 'Verified']
        if unverified_docs:
            return Response(
                {"error": "All submitted documents must be verified by staff before passport issuance."},
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

        # 3. Check Government Digital Signature
        sig = getattr(app, 'digital_signature', None)
        if not sig or not sig.is_valid:
            return Response(
                {"error": "Complete digital signature."},
                status=status.HTTP_400_BAD_REQUEST
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

            filename = f"Virtual_Passport_NP_{app.application_id:04d}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        except Exception as e:
            return Response({"error": f"Failed to generate PDF document: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-biometrics')
    def verify_biometrics(self, request, pk=None):
        """
        Staff or Admin action to update application biometric matching status.
        Supported statuses: 'Verified', 'Failed', 'Submitted', 'Pending'.
        """
        user_type = getattr(request.user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can verify biometrics."}, status=status.HTTP_403_FORBIDDEN)

        app = self.get_object()
        new_status = request.data.get('biometric_status')
        valid_choices = [c[0] for c in Application.BIOMETRIC_STATUS_CHOICES]
        if new_status not in valid_choices:
            return Response({"error": f"Invalid biometric_status. Must be one of: {', '.join(valid_choices)}"}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('remarks', '').strip()
        app.biometric_status = new_status
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
    def authorize_signature(self, request, pk=None):
        """
        Staff or Administrator authorization to issue Government Digital Signature.
        Strictly gated: Payment must already be verified, and passport photo verified!
        """
        user_type = getattr(request.user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only authorized Staff or Administrator can issue digital signatures."}, status=status.HTTP_403_FORBIDDEN)

        app = self.get_object()

        # STRICT PAYMENT GATE: Payment must be verified prior to digital signature authorization
        from django.db.models import Q
        is_paid = app.payments.filter(Q(status='VERIFIED') | Q(payment_status='Completed')).exists()
        if not is_paid:
            return Response(
                {"error": "Payment has not been verified yet. Applications cannot be signed or issued before verified payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # STRICT PHOTO GATE: Passport photo must be verified
        docs = list(app.documents.all()) if hasattr(app, 'documents') else []
        photo_doc = next((d for d in docs if 'photo' in (d.document_type or '').lower()), None)
        if not photo_doc or photo_doc.verification_status != 'Verified':
            return Response(
                {"error": "Passport-size photograph must be verified by staff before authorizing digital signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update application status to Approved if not already Completed
        if app.status != 'Completed':
            app.status = 'Approved'
        if getattr(app, 'biometric_status', None) != 'Verified':
            app.biometric_status = 'Verified'

        # Record issue date and expiry date if not yet set
        if not app.issue_date:
            from django.conf import settings
            validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
            app.issue_date = timezone.localdate()
            app.expiry_date = app.issue_date.replace(year=app.issue_date.year + validity)
        app.save()

        # Ensure DigitalSignature
        sig = getattr(app, 'digital_signature', None)
        if not sig:
            hash_str = f"NPL-DOP-{app.application_id}-{int(time.time())}"
            sig_hash = f"SHA256:{hashlib.sha256(hash_str.encode()).hexdigest()}"
            sig = DigitalSignature.objects.create(
                application=app,
                signature_hash=sig_hash,
                signing_authority="Department of Passports, Government of Nepal",
                certificate_serial=f"NPL-DOP-PKI-2026-{app.application_id:04d}",
                algorithm="RSA-SHA256",
                is_valid=True
            )
        else:
            sig.is_valid = True
            sig.save()

        # Complete queue token if present
        if hasattr(app, 'queue_token') and app.queue_token:
            app.queue_token.queue_status = 'Completed'
            app.queue_token.save()

        # Notify citizen
        if app.applicant:
            try:
                Notification.objects.create(
                    applicant=app.applicant,
                    application=app,
                    type='Digital Signature Authorized',
                    message=f"Government Digital Signature authorized for application #NP-{app.application_id:04d}.",
                    status='Unread'
                )
            except Exception:
                pass

        return Response({
            "message": f"Government Digital Signature authorized. Application #NP-{app.application_id:04d} marked as Approved.",
            "certificate_serial": sig.certificate_serial,
            "signature_hash": sig.signature_hash,
            "status": app.status,
            "issue_date": str(app.issue_date) if app.issue_date else None,
            "expiry_date": str(app.expiry_date) if app.expiry_date else None,
            "passport_status": app.passport_status
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='simulate-expiry')
    def simulate_expiry(self, request, pk=None):
        """
        Simulates passport expiry for testing and validation of the renewal workflow.
        Sets expiry_date to yesterday and status to Completed.
        """
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

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return Document.objects.filter(application__applicant_id=user_id).order_by('-document_id')
        return Document.objects.all().order_by('-document_id')

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

        if not uploaded_file:
            raise ValidationError({"file_path": "Uploaded document file is required."})

        if uploaded_file.size == 0:
            raise ValidationError({"file_path": "Uploaded file is empty (0 bytes)."})

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        if ext not in allowed_extensions:
            raise ValidationError({"file_path": "Invalid file format. Only PDF, JPG, and PNG documents are supported."})

        header = uploaded_file.read(8)
        uploaded_file.seek(0)

        if doc_type == 'Passport Photo':
            if ext not in ['.jpg', '.jpeg', '.png']:
                raise ValidationError({"file_path": "Passport photograph must be in JPG, JPEG, or PNG format."})
            if uploaded_file.size > 5 * 1024 * 1024:
                raise ValidationError({"file_path": "Passport photograph file size must not exceed 5MB."})

            if ext in ['.jpg', '.jpeg'] and not header.startswith(b'\xff\xd8\xff'):
                raise ValidationError({"file_path": "Uploaded passport photograph is corrupted or not a valid image."})
            elif ext == '.png' and not header.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValidationError({"file_path": "Uploaded passport photograph is corrupted or not a valid image."})

            try:
                from PIL import Image
                img = Image.open(uploaded_file)
                img.verify()
                uploaded_file.seek(0)
            except ImportError:
                pass
            except Exception:
                raise ValidationError({"file_path": "Uploaded passport photograph is corrupted or not a valid image."})

            # Clean up previous passport photos for this application (e.g. replacing a rejected photo)
            existing_photos = Document.objects.filter(application=application, document_type='Passport Photo')
            if existing_photos.exists():
                for old_photo in existing_photos:
                    try:
                        if old_photo.file_path and os.path.exists(old_photo.file_path.path):
                            os.remove(old_photo.file_path.path)
                    except Exception:
                        pass
                existing_photos.delete()
        else:
            if uploaded_file.size > 10 * 1024 * 1024:
                raise ValidationError({"file_path": "Document file size must not exceed 10MB."})

            if ext in ['.jpg', '.jpeg']:
                if not header.startswith(b'\xff\xd8\xff'):
                    raise ValidationError({"file_path": "Uploaded image file is corrupted or not a valid image."})
            elif ext == '.png':
                if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValidationError({"file_path": "Uploaded image file is corrupted or not a valid image."})
            elif ext == '.pdf':
                if not header.startswith(b"%PDF-"):
                    raise ValidationError({"file_path": "Uploaded PDF file is corrupted or not a valid PDF document."})

            if ext in ['.jpg', '.jpeg', '.png']:
                try:
                    from PIL import Image
                    img = Image.open(uploaded_file)
                    img.verify()
                    uploaded_file.seek(0)
                except ImportError:
                    pass
                except Exception:
                    raise ValidationError({"file_path": "Uploaded image file is corrupted or not a valid image."})

            # Clean up rejected previous upload of the same document type
            rejected_prev = Document.objects.filter(application=application, document_type=doc_type, verification_status='Rejected')
            if rejected_prev.exists():
                for old_doc in rejected_prev:
                    try:
                        if old_doc.file_path and os.path.exists(old_doc.file_path.path):
                            os.remove(old_doc.file_path.path)
                    except Exception:
                        pass
                rejected_prev.delete()

        # Initial status for uploads is Pending and not yet inspected
        doc = serializer.save(verification_status='Pending', is_inspected=False)

        # Log activity
        try:
            ActivityLog.objects.create(
                application=doc.application,
                action_taken=f"Document uploaded: {doc.document_type} for application #NP-{doc.application.application_id:04d}"[:255]
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

        if not doc.file_path or not os.path.exists(doc.file_path.path):
            return Response({"error": "Document file not found on storage."}, status=status.HTTP_404_NOT_FOUND)

        # Automatically mark as inspected if staff or admin views it
        if user_type in ['staff', 'administrator']:
            if not doc.is_inspected:
                doc.is_inspected = True
                doc.save(update_fields=['is_inspected'])
                try:
                    actor_staff = Staff.objects.filter(staff_id=user_id).first() if user_type == 'staff' else None
                    actor_str = f"Staff #{actor_staff.staff_id}" if actor_staff else "Officer"
                    ActivityLog.objects.create(
                        application=doc.application,
                        action_taken=f"[{actor_str}] Inspected {doc.document_type} for application #NP-{doc.application.application_id:04d}"[:255]
                    )
                except Exception:
                    pass

        import mimetypes
        content_type, _ = mimetypes.guess_type(doc.file_path.path)
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
            f = open(doc.file_path.path, 'rb')
            filename = doc.file_name or os.path.basename(doc.file_path.name)
            response = FileResponse(f, content_type=content_type, as_attachment=False, filename=filename)
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['X-Frame-Options'] = 'SAMEORIGIN'
            return response
        except Exception as e:
            return Response({"error": f"Failed to open document file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'], url_path='mark-inspected')
    def mark_inspected(self, request, pk=None):
        """Staff marks document as visually inspected"""
        user = request.user
        user_type = getattr(user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can mark documents as inspected."}, status=status.HTTP_403_FORBIDDEN)

        doc = self.get_object()
        doc.is_inspected = True
        doc.save(update_fields=['is_inspected'])

        user_id = getattr(user, 'user_id', None)
        actor_staff = Staff.objects.filter(staff_id=user_id).first() if user_type == 'staff' else None
        actor_str = f"Staff #{actor_staff.staff_id}" if actor_staff else "Officer"
        try:
            ActivityLog.objects.create(
                application=doc.application,
                action_taken=f"[{actor_str}] Marked {doc.document_type} as inspected"[:255]
            )
        except Exception:
            pass

        return Response({
            "message": "Document marked as inspected.",
            "document_id": doc.document_id,
            "is_inspected": True
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='verify-document')
    def verify_document(self, request, pk=None):
        """Staff/Admin verification of a specific document"""
        user = request.user
        user_type = getattr(user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can verify documents."}, status=status.HTTP_403_FORBIDDEN)

        doc = self.get_object()

        # Check application match if provided in body
        app_id_req = request.data.get('application_id') or request.data.get('application')
        if app_id_req and str(doc.application_id) != str(app_id_req):
            return Response({"error": "Document does not belong to the requested application."}, status=status.HTTP_400_BAD_REQUEST)

        # STRICT INSPECTION GATE: Must be inspected before verification
        if not doc.is_inspected:
            return Response({
                "error": "Document must be opened and visually inspected before verification.",
                "document_id": doc.document_id,
                "is_inspected": False
            }, status=status.HTTP_400_BAD_REQUEST)

        remarks = request.data.get('remarks', '').strip()
        doc.verification_status = 'Verified'
        doc.rejection_reason = remarks if remarks else ''
        doc.save()

        # Activity log
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
            "is_inspected": doc.is_inspected
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject-document')
    def reject_document(self, request, pk=None):
        """Staff/Admin rejection of a specific document"""
        user = request.user
        user_type = getattr(user, 'user_type', None)
        if user_type not in ['staff', 'administrator']:
            return Response({"error": "Only Staff or Administrator can reject documents."}, status=status.HTTP_403_FORBIDDEN)

        doc = self.get_object()

        # Check application match if provided
        app_id_req = request.data.get('application_id') or request.data.get('application')
        if app_id_req and str(doc.application_id) != str(app_id_req):
            return Response({"error": "Document does not belong to the requested application."}, status=status.HTTP_400_BAD_REQUEST)

        reason = (request.data.get('reason') or request.data.get('remarks') or '').strip()
        if not reason:
            return Response({
                "error": "A rejection reason is required so the applicant can correct the issue."
            }, status=status.HTTP_400_BAD_REQUEST)

        doc.verification_status = 'Rejected'
        doc.rejection_reason = reason
        doc.save()

        # Activity log
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

        # Notify applicant
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
            "rejection_reason": reason
        }, status=status.HTTP_200_OK)


class DigitalSignatureViewSet(viewsets.ModelViewSet):
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

    def create(self, request, *args, **kwargs):
        app_id = request.data.get('application')
        if not app_id:
            return super().create(request, *args, **kwargs)

        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        try:
            app = Application.objects.get(application_id=app_id)
        except Application.DoesNotExist:
            return Response({"error": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        if user_type == 'applicant' and app.applicant_id != user_id:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        # Check if payment is verified
        from django.db.models import Q
        has_paid = app.payments.filter(Q(status='VERIFIED') | Q(payment_status='Completed')).exists()
        if not has_paid and app.status != 'Approved':
            return Response({"error": "Application fee must be paid and verified before signing."}, status=status.HTTP_400_BAD_REQUEST)

        # Create or retrieve valid signature
        sig = getattr(app, 'digital_signature', None)
        if not sig:
            hash_str = f"NPL-DOP-{app.application_id}-{int(time.time())}"
            sig_hash = f"SHA256:{hashlib.sha256(hash_str.encode()).hexdigest()}"
            sig = DigitalSignature.objects.create(
                application=app,
                signature_hash=sig_hash,
                signing_authority="Department of Passports, Government of Nepal",
                certificate_serial=f"NPL-DOP-PKI-2026-{app.application_id:04d}",
                algorithm="RSA-SHA256",
                is_valid=True
            )
        else:
            sig.is_valid = True
            sig.save()

        # Update application status to Approved if not already
        if app.status != 'Approved' and app.status != 'Completed':
            app.status = 'Approved'
            app.save()

        serializer = self.get_serializer(sig)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QueueTokenViewSet(viewsets.ModelViewSet):
    queryset = QueueToken.objects.all().order_by('token_number')
    serializer_class = QueueTokenSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return QueueToken.objects.filter(application__applicant_id=user_id).order_by('-token_id')
        return QueueToken.objects.all().order_by('token_number')

    def perform_update(self, serializer):
        token = serializer.save()
        if token.queue_status == 'Completed' and token.application:
            self._handle_token_completion(token)

    def _handle_token_completion(self, token):
        app = token.application
        if app:
            if app.status != 'Approved':
                app.status = 'Approved'
                app.save()

            # Ensure DigitalSignature
            try:
                if not hasattr(app, 'digital_signature'):
                    hash_str = f"NPL-DOP-{app.application_id}-{token.token_number}-{int(time.time())}"
                    sig_hash = f"SHA256:{hashlib.sha256(hash_str.encode()).hexdigest()}"
                    DigitalSignature.objects.create(
                        application=app,
                        signature_hash=sig_hash,
                        signing_authority="Department of Passports, Government of Nepal",
                        certificate_serial=f"NPL-DOP-PKI-2026-{app.application_id:04d}",
                        algorithm="RSA-SHA256",
                        is_valid=True
                    )
            except Exception:
                pass

            # Notify applicant
            if app.applicant:
                try:
                    Notification.objects.create(
                        applicant=app.applicant,
                        application=app,
                        type="Application Approved",
                        message=f"Congratulations! Your passport application #NP-{app.application_id:04d} has been approved and your Virtual e-Passport is issued.",
                        status="Unread"
                    )
                except Exception:
                    pass

    @action(detail=False, methods=['post'], url_path='call-next')
    def call_next(self, request):
        token = QueueToken.objects.filter(queue_status='Waiting').order_by('token_date', 'token_number').first()
        if not token:
            return Response({"message": "No pending citizens in waiting queue.", "token": None}, status=status.HTTP_200_OK)

        token.queue_status = 'Called'
        token.called_time = timezone.now()

        # If staff is calling, record staff assignment
        staff_id = getattr(request.user, 'user_id', None)
        if getattr(request.user, 'user_type', None) == 'staff' and staff_id:
            try:
                token.staff = Staff.objects.get(staff_id=staff_id)
                if token.application and not token.application.staff:
                    token.application.staff = token.staff
                    token.application.save()
            except Staff.DoesNotExist:
                pass

        token.save()
        serializer = self.get_serializer(token)
        return Response({"message": f"Token T-{token.token_number} called to Desk Counter.", "token": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        token = self.get_object()
        new_status = request.data.get('queue_status')
        valid_statuses = [choice[0] for choice in QueueToken.STATUS_CHOICES]
        if not new_status or new_status not in valid_statuses:
            return Response({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}, status=status.HTTP_400_BAD_REQUEST)

        token.queue_status = new_status
        token.save()

        # If completed, trigger completion logic
        if new_status == 'Completed':
            self._handle_token_completion(token)

        serializer = self.get_serializer(token)
        return Response({"message": f"Token status updated to {new_status}.", "token": serializer.data}, status=status.HTTP_200_OK)


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-report_id')
    serializer_class = ReportSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]


class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all().order_by('-log_id')
    serializer_class = ActivityLogSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-notification_id')
    serializer_class = NotificationSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)
        if user_type == 'applicant':
            return Notification.objects.filter(applicant_id=user_id).order_by('-notification_id')
        return Notification.objects.all().order_by('-notification_id')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        user_id = getattr(request.user, 'user_id', None)
        if user_id:
            Notification.objects.filter(applicant_id=user_id, status='Unread').update(status='Read')
        return Response({"message": "All notifications marked as read."}, status=status.HTTP_200_OK)


from .payment_service import PaymentService


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_id')
    serializer_class = PaymentSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

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
            raise ValidationError("Valid application is required for payment.")

        if user_type == 'applicant' and application.applicant_id != user_id:
            raise PermissionDenied("You may only make payments for your own applications.")

        expected_fee = application.fee_amount
        submitted_amount = serializer.validated_data.get('amount') or self.request.data.get('amount')
        if submitted_amount is not None:
            try:
                sub_dec = Decimal(str(submitted_amount))
                if sub_dec != Decimal(str(expected_fee)):
                    raise ValidationError({
                        "error": f"Incorrect payment amount: NPR {sub_dec:,.2f}. The selected package '{application.passport_category}' requires NPR {expected_fee:,.2f}.",
                        "expected_amount": float(expected_fee),
                        "submitted_amount": float(sub_dec)
                    })
            except (ValueError, TypeError):
                raise ValidationError("Invalid payment amount format.")

        serializer.save(
            applicant=application.applicant,
            amount=expected_fee
        )

    @action(detail=False, methods=['post'], url_path='create-request')
    def create_payment_request(self, request):
        """
        Initiates a discrete payable request for an application.
        Backend authoritatively calculates fee and generates unique QR code.
        """
        user = request.user
        user_type = getattr(user, 'user_type', None)
        user_id = getattr(user, 'user_id', None)

        app_id = request.data.get('application_id')
        payment_type = request.data.get('payment_type', 'APPLICATION_FEE')
        gateway_name = request.data.get('gateway_name', 'eSewa')

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
        payment = PaymentService.create_payment_request(
            application=application,
            applicant=applicant,
            payment_type=payment_type,
            gateway_name=gateway_name
        )

        return Response({
            "message": "Payment request initiated successfully.",
            "payment_id": payment.payment_id,
            "payment_reference": payment.payment_reference,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_type": payment.payment_type,
            "status": payment.status,
            "gateway_name": payment.gateway_name,
            "qr_code": payment.qr_code,
            "qr_payload": payment.qr_payload,
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
        Sanitized status polling endpoint used by frontend every 3-5 seconds.
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
        reference = request.data.get('payment_reference')
        if not reference:
            return Response({"error": "payment_reference is required for simulation."}, status=status.HTTP_400_BAD_REQUEST)

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


@api_view(['POST'])
def login_view(request):
    identifier = (request.data.get('email') or request.data.get('username') or '').strip()
    password = request.data.get('password')

    if not identifier or not password:
        return Response(
            {
                "error": "Email/username and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Check Administrator (by email or username)
    administrator = Administrator.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()

    if administrator and check_password(password, administrator.password):
        if not administrator.is_active:
            return Response(
                {"error": "Administrator account is deactivated. Contact system admin."},
                status=status.HTTP_403_FORBIDDEN
            )

        token = secrets.token_hex(32)
        AuthToken.objects.create(
            token=token,
            user_type="administrator",
            user_id=administrator.admin_id
        )

        ActivityLog.objects.create(
            administrator=administrator,
            action_taken=f"Administrator logged in: {administrator.full_name} ({administrator.username or administrator.email})"
        )

        return Response({
            "message": "Login successful.",
            "role": "administrator",
            "user_id": administrator.admin_id,
            "name": administrator.full_name,
            "username": administrator.username,
            "email": administrator.email,
            "token": token
        }, status=status.HTTP_200_OK)

    # 2. Check Staff (by email or username)
    staff = Staff.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()

    if staff and check_password(password, staff.password):
        if not staff.is_active or staff.status != "Active":
            return Response(
                {"error": "Staff account is inactive or deactivated."},
                status=status.HTTP_403_FORBIDDEN
            )

        token = secrets.token_hex(32)
        AuthToken.objects.create(
            token=token,
            user_type="staff",
            user_id=staff.staff_id
        )

        return Response({
            "message": "Login successful.",
            "role": "staff",
            "user_id": staff.staff_id,
            "name": staff.full_name,
            "username": staff.username,
            "email": staff.email,
            "department": staff.department,
            "designation": staff.designation,
            "token": token
        }, status=status.HTTP_200_OK)

    # 3. Check Citizen / Applicant (by email)
    applicant = Applicant.objects.filter(email__iexact=identifier).first()

    if applicant and check_password(password, applicant.password):
        token = secrets.token_hex(32)
        AuthToken.objects.create(
            token=token,
            user_type="applicant",
            user_id=applicant.applicant_id
        )

        return Response({
            "message": "Login successful.",
            "role": "citizen",
            "user_id": applicant.applicant_id,
            "name": applicant.full_name,
            "email": applicant.email,
            "token": token
        }, status=status.HTTP_200_OK)

    return Response(
        {
            "error": "Invalid email/username or password."
        },
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
def register_view(request):
    role = request.data.get('role', 'citizen').lower()

    # Enforce that Staff and Administrator accounts cannot be registered publicly
    if role in ('staff', 'administrator'):
        return Response(
            {
                "error": "Staff and Administrator accounts cannot be registered publicly. Only an authorized Administrator can provision personnel."
            },
            status=status.HTTP_403_FORBIDDEN
        )

    if role != 'citizen':
        return Response({'error': 'Invalid registration role.'}, status=status.HTTP_400_BAD_REQUEST)

    common_fields = ['full_name', 'email', 'phone', 'password']
    missing_fields = [field for field in common_fields if not request.data.get(field)]
    required_fields = ['date_of_birth', 'gender', 'address']
    missing_fields.extend(field for field in required_fields if not request.data.get(field))

    if missing_fields:
        return Response(
            {'error': f"Missing required fields: {', '.join(missing_fields)}."},
            status=status.HTTP_400_BAD_REQUEST
        )

    raw_phone = str(request.data.get('phone', '')).strip()
    # Normalize phone: remove +977, spaces, hyphens
    cleaned_phone = re.sub(r'[\s\-+]', '', raw_phone)
    if cleaned_phone.startswith('977') and len(cleaned_phone) == 13:
        cleaned_phone = cleaned_phone[3:]

    # Nepal mobile format check: 10 digits starting with 98, 97, 96
    if not re.match(r'^9[678]\d{8}$', cleaned_phone):
        return Response(
            {'error': 'Invalid phone number format. Please enter a valid 10-digit Nepali mobile number (e.g. 98XXXXXXXX).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check duplicate phone upfront
    if Applicant.objects.filter(phone=cleaned_phone).exists():
        return Response(
            {'error': 'This phone number is already registered. Please use another phone number or log in to your existing account.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check duplicate email upfront
    email = str(request.data.get('email', '')).strip().lower()
    if Applicant.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'This email address is already registered. Please use another email or log in.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    fields = {
        'full_name': request.data.get('full_name'),
        'email': email,
        'phone': cleaned_phone,
        'password': request.data.get('password'),
        'date_of_birth': request.data.get('date_of_birth'),
        'gender': request.data.get('gender'),
        'nationality': request.data.get('nationality', 'Nepali'),
        'address': request.data.get('address'),
    }

    try:
        user = Applicant.objects.create(**fields)
    except IntegrityError as error:
        err_msg = str(error)
        if 'phone' in err_msg.lower():
            return Response(
                {'error': 'This phone number is already registered. Please use another phone number or log in to your existing account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'email' in err_msg.lower():
            return Response(
                {'error': 'This email address is already registered. Please use another email or log in.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({'error': 'Registration could not be completed due to a data conflict.'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as error:
        return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'message': 'Registration successful. You can now log in.',
        'role': 'citizen',
        'user_id': user.applicant_id,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def track_application_view(request):
    """
    Public safe endpoint to track application status by application_id or token_number.
    Does not expose sensitive personal information.
    """
    query = request.query_params.get('query') or request.query_params.get('id')
    if not query:
        return Response(
            {"error": "Please provide an application ID or token number to track."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Clean query (remove 'NP-', '#', or whitespace)
    cleaned_query = query.upper().replace('NP-', '').replace('NP', '').replace('#', '').strip()

    application = None

    # 1. Try finding by application_id
    if cleaned_query.isdigit():
        application = Application.objects.filter(application_id=int(cleaned_query)).first()

    # 2. Try finding by QueueToken token_number
    if not application and cleaned_query.isdigit():
        token = QueueToken.objects.filter(token_number=int(cleaned_query)).first()
        if token:
            application = token.application

    if not application:
        return Response(
            {"error": f"No application found matching reference '{query}'."},
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

    # Fetch Queue Token if exists
    token_data = None
    if hasattr(application, 'queue_token') and application.queue_token:
        token = application.queue_token
        token_data = {
            "token_number": token.token_number,
            "queue_status": token.queue_status,
            "token_date": str(token.token_date),
            "time_slot": str(token.time_slot) if token.time_slot else None,
            "called_time": str(token.called_time) if token.called_time else None,
        }

    # Document stats
    docs = application.documents.all()
    total_docs = docs.count()
    verified_docs = docs.filter(verification_status="Verified").count()

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
        "queue_token": token_data,
        "steps": application.get_workflow_steps(),
    }

    return Response(response_data, status=status.HTTP_200_OK)