from django.db import models
from django.contrib.auth.hashers import identify_hasher, make_password
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import hashlib
import secrets
import uuid


def generate_auth_token():
    """Compatibility callable retained for historical migration 0016."""
    return secrets.token_hex(32)


def hash_auth_token(raw_token):
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _password_changed(model, pk_name, instance):
    pk = getattr(instance, pk_name, None)
    if not pk:
        return False
    old_password = model.objects.filter(**{pk_name: pk}).values_list('password', flat=True).first()
    return bool(old_password and old_password != instance.password)


def _revoke_user_tokens(user_type, user_id):
    AuthToken.objects.filter(
        user_type=user_type,
        user_id=user_id,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


def _prepare_password(value):
    """Hash raw passwords while preserving encoded and unusable values."""
    value = str(value or '')
    if value.startswith('!'):
        return value
    try:
        identify_hasher(value)
        return value
    except ValueError:
        return make_password(value)


# 1. APPLICANT

class Applicant(models.Model):
    applicant_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=128)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    nationality = models.CharField(max_length=50, default="Nepali")
    address = models.CharField(max_length=255)
    email_verified_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    @property
    def phone_number(self):
        return self.phone

    @phone_number.setter
    def phone_number(self, value):
        self.phone = value

    def save(self, *args, **kwargs):
        password_changed = _password_changed(Applicant, 'applicant_id', self)
        self.password = _prepare_password(self.password)
        super().save(*args, **kwargs)
        if password_changed:
            _revoke_user_tokens('applicant', self.applicant_id)

    def __str__(self):
        return self.full_name



# 2. STAFF


class Staff(models.Model):
    staff_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    department = models.CharField(max_length=100, default="Document Verification")
    designation = models.CharField(max_length=100, default="Verification Officer")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default="Active")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def phone_number(self):
        return self.phone

    @phone_number.setter
    def phone_number(self, value):
        self.phone = value

    def save(self, *args, **kwargs):
        password_changed = _password_changed(Staff, 'staff_id', self)
        self.password = _prepare_password(self.password)
        # Sync status and is_active
        if not self.is_active or self.status == "Inactive":
            self.status = "Inactive"
            self.is_active = False
        else:
            self.status = "Active"
            self.is_active = True
        super().save(*args, **kwargs)
        if password_changed:
            _revoke_user_tokens('staff', self.staff_id)

    def __str__(self):
        return f"{self.full_name} ({self.username or self.email})"



# 3. ADMINISTRATOR


class Administrator(models.Model):
    admin_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def administrator_id(self):
        return self.admin_id

    @property
    def phone_number(self):
        return self.phone

    @phone_number.setter
    def phone_number(self, value):
        self.phone = value

    def save(self, *args, **kwargs):
        password_changed = _password_changed(Administrator, 'admin_id', self)
        self.password = _prepare_password(self.password)
        super().save(*args, **kwargs)
        if password_changed:
            _revoke_user_tokens('administrator', self.admin_id)

    def __str__(self):
        return f"{self.full_name} ({self.username or self.email})"


# 4. APPLICATION


class Application(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Under Review", "Under Review"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Completed", "Completed"),
    ]

    BIOMETRIC_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Submitted", "Submitted"),
        ("Verified", "Verified"),
        ("Failed", "Failed"),
    ]

    application_id = models.AutoField(primary_key=True)

    tracking_reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # APPLICANT 1 : N APPLICATION
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    # STAFF 1 : N APPLICATION
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_applications"
    )

    submission_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    last_updated = models.DateTimeField(auto_now=True)
    processing_notes = models.TextField(blank=True, null=True)

    # Workflow Specific Fields
    passport_category = models.CharField(
        max_length=50,
        default="Ordinary (34 Pages)",
        blank=True,
        null=True
    )

    service_type = models.CharField(
        max_length=50,
        default="New Passport",
        blank=True,
        null=True
    )

    biometric_status = models.CharField(
        max_length=30,
        choices=BIOMETRIC_STATUS_CHOICES,
        default="Pending"
    )

    APPLICATION_TYPE_CHOICES = [
        ("NEW", "NEW"),
        ("RENEWAL", "RENEWAL"),
    ]

    application_type = models.CharField(
        max_length=20,
        choices=APPLICATION_TYPE_CHOICES,
        default="NEW"
    )

    # Application-location and appointment fields retained by the production
    # database. Defaults keep the shorter online application form valid while
    # allowing appointment details to be assigned later in the workflow.
    applying_within_nepal = models.BooleanField(default=True)

    appointment_date = models.DateField(
        null=True,
        blank=True
    )

    appointment_office = models.CharField(
        max_length=150,
        default="Department of Passports, Tripureshwor"
    )

    appointment_time = models.TimeField(
        null=True,
        blank=True
    )

    national_id_number = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    issue_date = models.DateField(
        null=True,
        blank=True
    )

    expiry_date = models.DateField(
        null=True,
        blank=True
    )

    passport_number = models.CharField(
        max_length=9,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="Sequential number assigned only when passport processing completes.",
    )

    @property
    def passport_status(self):
        """
        Determines if an issued passport is ACTIVE or EXPIRED based on timezone.localdate().
        Returns None if passport has not been issued (no expiry date recorded).
        """
        if self.status not in ['Approved', 'Completed'] or not self.expiry_date:
            return None
        from django.utils import timezone
        today = timezone.localdate()
        if today >= self.expiry_date:
            return "EXPIRED"
        return "ACTIVE"

    @property
    def is_expired(self):
        return self.passport_status == "EXPIRED"

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if not self.applicant_id:
            return

        existing_apps = Application.objects.filter(applicant_id=self.applicant_id)
        if self.pk:
            existing_apps = existing_apps.exclude(pk=self.pk)

        # 1. Reject if an in-progress or unsigned pre-payment application exists.
        # A signed Approved record represents the issued passport and must be
        # evaluated using its expiry date below.
        active_app = existing_apps.filter(status__in=['Pending', 'Under Review']).first()
        if not active_app:
            for approved_app in existing_apps.filter(status='Approved').order_by('-application_id'):
                signature = getattr(approved_app, 'digital_signature', None)
                if not (signature and signature.is_valid and approved_app.expiry_date):
                    active_app = approved_app
                    break
        if active_app:
            raise ValidationError(
                f"You already have an active passport application (#NP-{active_app.application_id:04d}). Another application cannot be submitted."
            )

        # 2. Check completed / issued passports
        completed_passports = existing_apps.filter(
            status__in=['Approved', 'Completed'],
            digital_signature__is_valid=True,
            expiry_date__isnull=False,
        ).order_by('-application_id')
        latest_completed = completed_passports.first()

        is_renewal_request = (
            self.application_type == 'RENEWAL' or
            'renewal' in (self.service_type or '').lower()
        )

        if latest_completed:
            p_status = latest_completed.passport_status
            if p_status == 'ACTIVE':
                exp_str = str(latest_completed.expiry_date) if latest_completed.expiry_date else 'active'
                raise ValidationError(
                    f"You already have an active passport (Valid until {exp_str}). Renewal is only permitted after expiration."
                )
            elif p_status == 'EXPIRED':
                if not is_renewal_request:
                    raise ValidationError(
                        "Your previous passport has expired. You must apply for a Renewal through the Renewal workflow, not a new passport application."
                    )
        else:
            if is_renewal_request:
                raise ValidationError(
                    "Cannot apply for passport renewal without a previously issued expired passport."
                )

    def save(self, *args, **kwargs):
        # Auto-set issue_date and expiry_date upon completion/approval with valid signature if not already set
        if self.status in ['Approved', 'Completed'] and not self.issue_date:
            sig = getattr(self, 'digital_signature', None)
            if sig and getattr(sig, 'is_valid', False):
                from django.utils import timezone
                from django.conf import settings
                validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
                self.issue_date = timezone.localdate()
                self.expiry_date = self.issue_date.replace(year=self.issue_date.year + validity)
        super().save(*args, **kwargs)


    @property
    def fee_amount(self):
        cat = (self.passport_category or "").lower()
        if "66" in cat:
            return 10000.00
        elif "urgent" in cat or "express" in cat:
            return 12000.00
        return 5000.00

    @property
    def passport_type(self):
        cat = (self.passport_category or "").lower()
        if "urgent" in cat or "express" in cat:
            return "Express Urgent e-Passport"
        return "Ordinary e-Passport"

    @property
    def passport_pages(self):
        cat = (self.passport_category or "").lower()
        if "66" in cat:
            return "66 Pages"
        return "34 Pages"

    @property
    def delivery_type(self):
        cat = (self.passport_category or "").lower()
        svc = (self.service_type or "").lower()
        if "urgent" in cat or "express" in cat or "urgent" in svc or "express" in svc:
            return "Fast-Track Delivery"
        return "Standard Delivery"

    @property
    def queue_position(self):
        try:
            token = getattr(self, 'queue_token', None)
            if not token or token.queue_status != 'Waiting':
                return 0
            from django.db.models import Q
            return QueueToken.objects.filter(
                Q(token_date=token.token_date, token_number__lt=token.token_number, queue_status='Waiting') |
                Q(token_date__lt=token.token_date, queue_status='Waiting')
            ).count() + 1
        except Exception:
            return 0

    def get_workflow_steps(self):
        """
        Computes the real-time status of all 9 steps for this application
        based on active PostgreSQL records.
        """
        def ordered_steps(steps):
            for index, workflow_step in enumerate(steps, start=1):
                workflow_step['step'] = index
            return steps

        # Keep the step presentation here, while deriving every workflow gate
        # from the same facts used by the API and download authorization.
        from .workflow_service import build_workflow_facts
        facts = build_workflow_facts(self)

        # Step 1: Citizen Registration / Login
        step1 = {
            "step": 1,
            "key": "registration",
            "title": "Citizen Registration / Login",
            "status": "Completed",
            "details": f"Registered citizen: {self.applicant.full_name if self.applicant else 'Citizen User'}",
            "action_url": "/applicant/profile/",
            "action_label": "View Profile"
        }

        # Step 2: Fill Application
        step2 = {
            "step": 2,
            "key": "application",
            "title": "Fill Application",
            "status": "Completed",
            "details": f"Application #NP-{self.application_id:04d} ({self.passport_category or 'Ordinary 34 Pages'})",
            "action_url": "/applicant/apply/",
            "action_label": "Application Details"
        }

        # Step 3: Upload Required Documents
        docs = facts['documents']
        doc_count = len(docs)
        verified_count = len(facts['verified_documents'])
        rejected_count = len(facts['rejected_documents'])

        photo_doc = facts['photo']
        has_photo = bool(photo_doc)
        photo_verified = facts['photo_verified']
        photo_rejected = facts['photo_rejected']
        has_identity = facts['has_identity']

        if doc_count == 0:
            doc_status = "Action Required"
            doc_details = "Awaiting document uploads (Citizenship Certificate & Passport Photo required)"
        elif not has_photo:
            doc_status = "Action Required"
            doc_details = "Passport-size photo is required before continuing."
        elif not has_identity:
            doc_status = "Action Required"
            doc_details = "Citizenship Certificate or National ID is required before continuing."
        elif photo_rejected:
            doc_status = "Action Required"
            doc_details = f"Passport photo rejected: {photo_doc.rejection_reason or 'Please re-upload a valid photo.'}"
        elif rejected_count > 0:
            doc_status = "Action Required"
            doc_details = f"{rejected_count} document(s) flagged/rejected. Please re-upload."
        else:
            doc_status = "Completed"
            doc_details = f"All {doc_count} required document upload(s) received"

        step3 = {
            "step": 3,
            "key": "documents",
            "title": "Upload Required Documents",
            "status": doc_status,
            "details": doc_details,
            "action_url": "/applicant/documents/",
            "action_label": "Upload / View Documents",
            "has_photo": has_photo,
            "photo_verified": photo_verified,
            "has_identity_document": has_identity,
        }

        # Step 8: Queue / Processing. This remains locked until signing.
        token = facts['queue_token']
        token_status = "Locked"
        token_details = "Locked until the government digital signature is authorized"

        step4 = {
            "step": 4,
            "key": "queue",
            "title": "Queue / Processing",
            "status": token_status,
            "details": token_details,
            "action_url": "/applicant/queue/",
            "action_label": "View Token"
        }
        # Step 4: Payment
        verified_payment = facts['verified_payment']
        active_payment = None
        if hasattr(self, 'payments'):
            active_payment = self.payments.exclude(
                payment_reference__isnull=True
            ).exclude(payment_reference='').order_by('-payment_id').first()

        fee_val = self.fee_amount
        # STRICT PAYMENT GATE: Only actual verified payment record marks payment as verified
        is_payment_verified = facts['payment_verified']

        if verified_payment:
            fee_status = "Completed"
            gw = verified_payment.gateway_name or verified_payment.payment_method or "Online Gateway"
            ref = verified_payment.payment_reference or verified_payment.transaction_id or f"TXN-{verified_payment.payment_id}"
            fee_details = f"Fee of NPR {verified_payment.amount:,.0f} verified via {gw} (Ref: {ref})"
            action_label = "Payment Receipt"
        elif not (has_photo and has_identity) or rejected_count > 0:
            fee_status = "Locked"
            fee_details = "Payment unlocks after all required current documents are uploaded"
            action_label = "Upload Documents First"
        elif active_payment and active_payment.status in ['PENDING', 'QR_GENERATED', 'PAYMENT_INITIATED', 'PAID']:
            fee_status = "Payment Initiated"
            fee_details = (
                f"eSewa payment of NPR {active_payment.amount:,.0f} "
                f"({active_payment.payment_reference}) is awaiting completion or verification"
            )
            action_label = "Continue Payment"
        else:
            fee_status = "Payment Required"
            fee_details = f"Statutory tariff: NPR {fee_val:,.0f} for {self.passport_category or 'Ordinary 34 Pages'}"
            action_label = "Pay Fee Online"

        step5 = {
            "step": 5,
            "key": "fee",
            "title": "Payment",
            "status": fee_status,
            "details": fee_details,
            "action_url": "/applicant/apply/",
            "action_label": action_label,
            "is_verified": is_payment_verified,
            "fee_amount": fee_val,
        }

        document_review_complete = facts['documents_complete']

        # Payment precedes staff document verification and every later stage.
        if not is_payment_verified:
            step6 = {
                "step": 6,
                "key": "biometrics",
                "title": "Biometrics Verification",
                "status": "Completed" if getattr(self, 'biometric_status', None) == 'Verified' else "Locked",
                "details": "Biometrics verified" if getattr(self, 'biometric_status', None) == 'Verified' else "Locked until application fee payment is verified with the gateway",
                "action_url": "/applicant/apply/",
                "action_label": "Fee Required First"
            }
            step7 = {
                "step": 7,
                "key": "verification",
                "title": "Staff Document Verification",
                "status": "Completed" if document_review_complete else "Locked",
                "details": "All current documents verified by staff" if document_review_complete else "Locked until application fee payment is verified",
                "action_url": "/applicant/documents/",
                "action_label": "View Document Status" if document_review_complete else "Awaiting Fee"
            }
            step8 = {
                "step": 8,
                "key": "signature",
                "title": "Digital Signature",
                "status": "Locked",
                "details": "Locked until payment is verified with the gateway",
                "action_url": "/applicant/apply/",
                "action_label": "Locked"
            }
            step9 = {
                "step": 9,
                "key": "passport_ready",
                "title": "Passport Generation",
                "status": "Locked",
                "details": "Locked until application fee payment is verified with the gateway",
                "action_url": "/applicant/apply/",
                "action_label": "Locked",
                "can_download": False
            }
            return ordered_steps([step1, step2, step3, step5, step7, step6, step8, step4, step9])

        # Step 6: Biometrics Verification
        b_status = getattr(self, 'biometric_status', 'Pending') or 'Pending'

        if not document_review_complete:
            bio_status = "Locked"
            bio_details = "Locked until all current required documents are verified by staff"
        elif b_status == 'Verified':
            bio_status = "Completed"
            bio_details = "Digital biometrics and photograph verified against standards"
        elif b_status == 'Failed':
            bio_status = "Rejected"
            bio_details = "Biometric match criteria not met. Re-submission needed"
        elif b_status == 'Submitted' or has_photo:
            bio_status = "Pending Verification"
            bio_details = "Applicant credentials and photo queued for electronic validation"
        else:
            bio_status = "Action Required"
            bio_details = "Please upload applicant photograph for digital biometric processing"

        step6 = {
            "step": 6,
            "key": "biometrics",
            "title": "Biometrics Verification",
            "status": bio_status,
            "details": bio_details,
            "action_url": "/applicant/documents/",
            "action_label": "Biometric Details"
        }

        # Step 5: Staff Document Verification
        if rejected_count > 0:
            staff_status = "Rejected"
            staff_details = f"Document rejected: {self.processing_notes or 'A replacement upload is required'}"
        elif document_review_complete:
            staff_status = "Completed"
            officer = self.staff.full_name if self.staff else "Desk Officer"
            staff_details = f"All current required documents verified by {officer}"
        elif self.status == 'Under Review':
            staff_status = "In Progress"
            staff_details = "Desk officer currently examining submitted documents and claims"
        else:
            staff_status = "Pending Verification"
            staff_details = "Awaiting verification officer assignment"

        step7 = {
            "step": 7,
            "key": "verification",
            "title": "Staff Document Verification",
            "status": staff_status,
            "details": staff_details,
            "action_url": "/applicant/documents/",
            "action_label": "View Document Status"
        }

        # Step 7: Digital Signature
        sig = facts['signature']
        if facts['signature_is_valid']:
            sig_status = "Completed"
            sig_details = f"Digitally signed by {sig.signing_authority} • Cert: {sig.certificate_serial} ({sig.algorithm})"
        elif document_review_complete and is_payment_verified and b_status == 'Verified':
            sig_status = "In Progress"
            sig_details = "Payment verified; ready for digital signature authorization"
        elif not document_review_complete:
            sig_status = "Locked"
            sig_details = "Locked until all current required documents are verified"
        elif b_status != 'Verified':
            sig_status = "Locked"
            sig_details = "Locked until biometric verification is completed"
        else:
            sig_status = "Not Started"
            sig_details = "Ready after document, payment, and biometric verification are completed"

        step8 = {
            "step": 8,
            "key": "signature",
            "title": "Digital Signature",
            "status": sig_status,
            "details": sig_details,
            "action_url": "/applicant/dashboard/",
            "action_label": "View Signature"
        }

        # The processing queue begins only after a valid signature exists.
        if facts['signature_is_valid']:
            if token:
                q_pos = self.queue_position
                pos_text = f" • Position #{q_pos} in line" if q_pos > 0 else ""
                token_status = "Completed" if token.queue_status == "Completed" else "In Progress"
                token_details = (
                    f"Token T-{token.token_number:03d} "
                    f"(Status: {token.queue_status}{pos_text})"
                )
            else:
                token_status = "In Progress"
                token_details = "Digital signature authorized; processing token is being assigned"
            step4.update({
                "status": token_status,
                "details": token_details,
                "action_label": "View Processing Token",
            })

        # Step 9: Passport Generation
        queue_processing_complete = facts['queue_complete']
        # STRICT ISSUANCE GATE: every preceding stage, including processing, must be complete.
        can_download = facts['can_download']
        if can_download:
            passport_status = "Completed"
            passport_details = "Official Virtual e-Passport is active, certified, and ready for use"
        elif not is_payment_verified:
            passport_status = "Locked"
            passport_details = "Locked until application fee payment is verified with the gateway"
        elif not facts['signature_is_valid']:
            passport_status = "Locked"
            passport_details = "Locked until government digital signature is authorized"
        elif not queue_processing_complete:
            passport_status = "Locked"
            passport_details = "Locked until queue processing is completed by staff"
        elif not photo_verified:
            passport_status = "Locked"
            passport_details = "Locked until passport-size photo is verified by staff"
        elif self.status in ['Approved', 'Completed']:
            passport_status = "In Progress"
            passport_details = "Finalizing electronic certificate and virtual document"
        else:
            passport_status = "Not Started"
            passport_details = "Issued immediately upon successful completion of preceding stages"

        step9 = {
            "step": 9,
            "key": "passport_ready",
            "title": "Passport Generation",
            "status": passport_status,
            "details": passport_details,
            "action_url": f"/api/applications/{self.application_id}/download-pdf/",
            "action_label": "Download Virtual Passport PDF",
            "can_download": can_download
        }

        return ordered_steps([step1, step2, step3, step5, step7, step6, step8, step4, step9])

    def get_current_documents(self):
        """Return the newest active version of each logical document requirement."""
        if not hasattr(self, 'documents'):
            return []

        current_documents = []
        seen_types = set()
        for document in self.documents.all().order_by('-document_id'):
            type_key = self.document_type_group(document.document_type)
            if type_key in seen_types:
                continue
            seen_types.add(type_key)
            current_documents.append(document)
        return current_documents

    @staticmethod
    def document_type_group(document_type):
        """Group Citizenship and National ID as alternative identity evidence."""
        type_key = (document_type or '').strip().casefold()
        if (
            'citizenship' in type_key
            or type_key.startswith('national id')
            or type_key == 'nid'
        ):
            return 'identity-document'
        return type_key

    def __str__(self):
        return f"Application #{self.application_id}"

# 5. DOCUMENT

class Document(models.Model):

    VERIFICATION_CHOICES = [
        ("Pending", "Pending"),
        ("Verified", "Verified"),
        ("Rejected", "Rejected"),
    ]

    document_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : N DOCUMENT
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(max_length=100)

    file_name = models.CharField(max_length=255)

    file_path = models.FileField(
        upload_to="documents/"
    )

    upload_date = models.DateTimeField(auto_now_add=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default="Pending"
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    is_inspected = models.BooleanField(
        default=False,
        help_text="Tracks whether staff/admin has opened and visually inspected the uploaded document file."
    )

    def __str__(self):
        return self.document_type

# 6. DIGITAL SIGNATURE


class DigitalSignature(models.Model):

    signature_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : 1 DIGITAL SIGNATURE
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="digital_signature"
    )

    # Base64-encoded RSA-PSS signature. The historical field name is retained
    # so existing API clients do not break.
    signature_hash = models.TextField()

    payload_hash = models.CharField(max_length=64, blank=True, default="")

    credential_schema = models.CharField(
        max_length=50,
        default="np-passport-credential-v1",
    )

    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    key_id = models.CharField(max_length=100, blank=True, default="")

    signing_authority = models.CharField(
        max_length=150,
        default="Department of Passports, Ministry of Foreign Affairs, Government of Nepal"
    )

    certificate_serial = models.CharField(
        max_length=100,
        default="NPL-DOP-PKI-2026-001"
    )

    algorithm = models.CharField(
        max_length=50,
        default="RSA-PSS-SHA256"
    )

    signed_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    is_valid = models.BooleanField(
        default=False
    )

    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Sig #{self.signature_id} for App #{self.application_id} ({self.algorithm})"


class PassportNumberSequence(models.Model):
    """Single locked row used to allocate gap-free issued passport numbers."""

    sequence_id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_value = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Passport number sequence"
        verbose_name_plural = "Passport number sequence"

    def __str__(self):
        return f"Passport sequence at {self.last_value}"

# 7. QUEUE TOKEN

class QueueToken(models.Model):

    STATUS_CHOICES = [
        ("Waiting", "Waiting"),
        ("Called", "Called"),
        ("Serving", "Serving"),
        ("Completed", "Completed"),
        ("Skipped", "Skipped"),
    ]

    token_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : 1 QUEUE TOKEN
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="queue_token"
    )

    # STAFF 1 : N QUEUE TOKEN
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queue_tokens"
    )

    token_number = models.PositiveIntegerField()

    token_date = models.DateField(
        auto_now_add=True
    )

    time_slot = models.TimeField(
        null=True,
        blank=True
    )

    queue_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Waiting"
    )

    called_time = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Token #{self.token_number} - {self.queue_status}"


# 8. REPORT

class Report(models.Model):

    report_id = models.AutoField(primary_key=True)

    # ADMINISTRATOR 1 : N REPORT
    administrator = models.ForeignKey(
        Administrator,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    report_type = models.CharField(
        max_length=100
    )

    generated_date = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    data_payload = models.JSONField(
        default=dict,
        blank=True
    )

    def __str__(self):
        return self.report_type

# 9. ACTIVITY LOG

class ActivityLog(models.Model):

    log_id = models.AutoField(primary_key=True)

    # Optional administrator for system/applicant logged events
    administrator = models.ForeignKey(
        Administrator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs"
    )

    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    action_taken = models.CharField(
        max_length=255
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.action_taken

# 10. NOTIFICATION

class Notification(models.Model):

    STATUS_CHOICES = [
        ("Unread", "Unread"),
        ("Read", "Read"),
    ]

    notification_id = models.AutoField(primary_key=True)

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    type = models.CharField(max_length=50)

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Unread"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.message[:50]

# 11. PAYMENT

class Payment(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("QR_GENERATED", "QR_GENERATED"),
        ("PAYMENT_INITIATED", "PAYMENT_INITIATED"),
        ("PAID", "PAID"),
        ("VERIFIED", "VERIFIED"),
        ("FAILED", "FAILED"),
        ("EXPIRED", "EXPIRED"),
        ("CANCELLED", "CANCELLED"),
    ]

    LEGACY_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    ]

    PAYMENT_TYPE_CHOICES = [
        ("APPLICATION_FEE", "Application Fee"),
        ("URGENT_PROCESSING_FEE", "Urgent Processing Fee"),
        ("ADDITIONAL_SERVICE_FEE", "Additional Service Fee"),
    ]

    METHOD_CHOICES = [
        ("eSewa", "eSewa"),
        ("Khalti", "Khalti"),
        ("ConnectIPS", "ConnectIPS"),
        ("Bank Transfer", "Bank Transfer"),
        ("Digital Wallet", "Digital Wallet"),
        ("Sandbox Gateway", "Sandbox Gateway"),
        ("Online", "Online"),
    ]

    payment_id = models.AutoField(primary_key=True)

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="NPR"
    )

    payment_type = models.CharField(
        max_length=50,
        choices=PAYMENT_TYPE_CHOICES,
        default="APPLICATION_FEE"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=LEGACY_STATUS_CHOICES,
        default="Pending"
    )

    payment_method = models.CharField(
        max_length=50,
        choices=METHOD_CHOICES,
        default="eSewa"
    )

    gateway_name = models.CharField(
        max_length=50,
        default="eSewa",
        blank=True,
        null=True
    )

    qr_code = models.TextField(
        blank=True,
        null=True,
        help_text="SVG or Base64 Data URI of payment QR code"
    )

    qr_payload = models.TextField(
        blank=True,
        null=True,
        help_text="Standardized payload encoded in QR code"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    remarks = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        # Synchronize status and payment_status
        if self.status == "VERIFIED":
            self.payment_status = "Completed"
        elif self.status in ["FAILED", "CANCELLED", "EXPIRED"]:
            self.payment_status = "Failed"
        elif self.payment_status == "Completed" and self.status in ["PENDING", "QR_GENERATED", "PAYMENT_INITIATED"]:
            self.status = "VERIFIED"
        super().save(*args, **kwargs)

    def __str__(self):
        ref = self.payment_reference or f"ID-{self.payment_id}"
        return f"Payment [{ref}] - App #{self.application_id} - {self.amount} {self.currency} ({self.status})"


class AuthToken(models.Model):
    token_id = models.AutoField(primary_key=True)

    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    user_type = models.CharField(
        max_length=20
    )

    user_id = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    revoked_at = models.DateTimeField(null=True, blank=True)

    last_used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, user_type, user_id):
        raw_token = secrets.token_urlsafe(48)
        ttl = max(1, getattr(settings, 'AUTH_TOKEN_TTL_MINUTES', 720))
        token = cls.objects.create(
            token_hash=hash_auth_token(raw_token),
            user_type=user_type,
            user_id=user_id,
            expires_at=timezone.now() + timedelta(minutes=ttl),
        )
        return raw_token, token

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])

    def __str__(self):
        return f"Session #{self.token_id} ({self.user_type}:{self.user_id})"


class LoginAttempt(models.Model):
    """Hashed account/IP counters used for login throttling and lockout."""

    key_hash = models.CharField(max_length=64, unique=True)
    scope = models.CharField(max_length=20, choices=[('account', 'Account'), ('ip', 'IP')])
    attempts = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(default=timezone.now)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.scope} login limiter ({self.attempts})"
