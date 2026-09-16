"""
Payment Service Layer for Nepal Passport Office Document Preparation & Queue Management System.
Integrates eSewa ePay v2 while retaining the legacy sandbox helper with:
- Authoritative backend fee calculation
- Signed eSewa browser redirect requests
- Signed callback validation and server-to-server status verification
- Idempotent webhook handling with database transaction safety
- Clear separation between Sandbox/Dev and Production
"""

import base64
import binascii
import hmac
import hashlib
import json
import secrets
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.conf import settings

from .models import Payment, Application, Applicant, ActivityLog, Notification
from .qr_generator import generate_qr_data_uri, generate_qr_svg


class PaymentService:
    """
    Central business logic for payments and gateway integration.
    """

    ESEWA_SIGNED_REQUEST_FIELDS = (
        'total_amount',
        'transaction_uuid',
        'product_code',
    )
    ESEWA_REQUIRED_RESPONSE_FIELDS = {
        'transaction_code',
        'status',
        'total_amount',
        'transaction_uuid',
        'product_code',
        'signed_field_names',
        'signature',
    }

    # Backward-compatible names are retained because older system tests import
    # them directly.
    GATEWAY_URL = settings.ESEWA_PAYMENT_URL
    STATUS_URL = settings.ESEWA_STATUS_URL
    MERCHANT_ID = settings.ESEWA_PRODUCT_CODE
    GATEWAY_SECRET = settings.ESEWA_SECRET_KEY
    ENVIRONMENT = settings.ESEWA_ENVIRONMENT
    HTTP_TIMEOUT = settings.ESEWA_HTTP_TIMEOUT

    @classmethod
    def calculate_fee(cls, application: Application, payment_type: str = "APPLICATION_FEE") -> Decimal:
        """
        Authoritative backend fee calculation.
        Frontend values are strictly ignored.
        """
        cat = (getattr(application, 'passport_category', '') or '').lower()
        svc = (getattr(application, 'service_type', '') or '').lower()

        if payment_type == "APPLICATION_FEE":
            is_66 = "66" in cat
            is_urgent = ("urgent" in cat or "express" in cat or "urgent" in svc or "express" in svc)

            if is_66 and is_urgent:
                return Decimal("15000.00")
            elif is_66:
                return Decimal("10000.00")
            elif is_urgent:
                return Decimal("12000.00")
            else:
                return Decimal("5000.00")

        elif payment_type == "URGENT_PROCESSING_FEE":
            return Decimal("3000.00")

        elif payment_type == "ADDITIONAL_SERVICE_FEE":
            return Decimal("500.00")

        return Decimal("5000.00")

    @classmethod
    def calculate_tariff(cls, category: str) -> Decimal:
        """
        Calculates statutory tariff for a given category name.
        """
        cat = str(category or "").lower()
        if "dip" in cat or "official" in cat:
            return Decimal("15000.00")
        if "66" in cat:
            return Decimal("10000.00")
        if "urg" in cat or "express" in cat:
            return Decimal("12000.00")
        return Decimal("5000.00")

    @classmethod
    def validate_esewa_configuration(cls) -> None:
        """Reject test credentials when the application is in production mode."""
        if cls.ENVIRONMENT not in {'sandbox', 'uat', 'production'}:
            raise ValueError("ESEWA_ENVIRONMENT must be sandbox, uat, or production.")
        if not cls.GATEWAY_URL or not cls.STATUS_URL:
            raise ValueError("eSewa payment and status URLs must be configured.")
        if not cls.MERCHANT_ID or not cls.GATEWAY_SECRET:
            raise ValueError("eSewa merchant product code and secret key are required.")
        if cls.ENVIRONMENT == 'production' and (
            cls.MERCHANT_ID == 'EPAYTEST'
            or cls.GATEWAY_SECRET == '8gBm/:&EnhH.1/q'
        ):
            raise ValueError(
                "Production eSewa credentials are not configured. Set "
                "ESEWA_PRODUCT_CODE and ESEWA_SECRET_KEY."
            )

    @staticmethod
    def normalize_amount(value) -> Decimal:
        """Parse eSewa amounts, including responses formatted with commas."""
        return Decimal(str(value).replace(',', '').strip())

    @staticmethod
    def format_amount(value) -> str:
        """Return a fixed two-decimal representation used consistently for signing."""
        return format(PaymentService.normalize_amount(value).quantize(Decimal('0.01')), 'f')

    @classmethod
    def generate_esewa_signature(cls, message: str) -> str:
        """Generate the Base64 HMAC-SHA256 signature required by eSewa ePay v2."""
        digest = hmac.new(
            cls.GATEWAY_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode('utf-8')

    @classmethod
    def build_esewa_message(cls, values: dict, field_names) -> str:
        """Build eSewa's ordered comma-separated signature input."""
        return ','.join(f"{field}={values[field]}" for field in field_names)

    @classmethod
    def build_esewa_payment_form(
        cls,
        payment: Payment,
        success_url: str,
        failure_url: str,
    ) -> dict:
        """Create the complete signed form payload posted by the browser to eSewa."""
        cls.validate_esewa_configuration()
        total_amount = cls.format_amount(payment.amount)
        fields = {
            'amount': total_amount,
            'tax_amount': '0',
            'total_amount': total_amount,
            'transaction_uuid': payment.payment_reference,
            'product_code': cls.MERCHANT_ID,
            'product_service_charge': '0',
            'product_delivery_charge': '0',
            'success_url': success_url,
            'failure_url': failure_url,
            'signed_field_names': ','.join(cls.ESEWA_SIGNED_REQUEST_FIELDS),
        }
        message = cls.build_esewa_message(fields, cls.ESEWA_SIGNED_REQUEST_FIELDS)
        fields['signature'] = cls.generate_esewa_signature(message)
        return fields

    @classmethod
    def decode_and_verify_esewa_response(cls, encoded_data: str) -> dict:
        """Decode eSewa's Base64 return data and verify every required signed field."""
        if not encoded_data:
            raise ValueError("Missing eSewa response data.")

        normalized_data = encoded_data.strip().replace(' ', '+')
        normalized_data += '=' * (-len(normalized_data) % 4)
        try:
            decoded = base64.b64decode(normalized_data, validate=True).decode('utf-8')
            payload = json.loads(decoded)
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid eSewa response encoding.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Invalid eSewa response payload.")

        missing = cls.ESEWA_REQUIRED_RESPONSE_FIELDS.difference(payload)
        if missing:
            raise ValueError(
                f"eSewa response is missing required fields: {', '.join(sorted(missing))}."
            )

        signed_fields = [
            field.strip()
            for field in str(payload['signed_field_names']).split(',')
            if field.strip()
        ]
        required_signed_fields = cls.ESEWA_REQUIRED_RESPONSE_FIELDS.difference({'signature'})
        if not required_signed_fields.issubset(signed_fields):
            raise ValueError("eSewa did not sign all required response fields.")
        if 'signature' in signed_fields or any(field not in payload for field in signed_fields):
            raise ValueError("Invalid eSewa signed field list.")

        message = cls.build_esewa_message(payload, signed_fields)
        expected_signature = cls.generate_esewa_signature(message)
        if not hmac.compare_digest(str(payload['signature']), expected_signature):
            raise ValueError("Invalid eSewa response signature.")

        return payload

    @classmethod
    def generate_payment_reference(cls, application: Application, payment_type: str) -> str:
        """
        Generates unique, traceable payment reference.
        Example: PP-2026-0001-FEE, PP-2026-0001-URGENT, PP-2026-0001-SVC
        """
        year = timezone.now().year
        type_suffix = {
            "APPLICATION_FEE": "FEE",
            "URGENT_PROCESSING_FEE": "URGENT",
            "ADDITIONAL_SERVICE_FEE": "SVC"
        }.get(payment_type, "PAY")

        # Include application ID and unique randomness to guarantee absolute uniqueness
        app_id = application.application_id
        rand_salt = secrets.token_hex(2).upper()
        return f"PP-{year}-{app_id:04d}-{type_suffix}-{rand_salt}"

    @classmethod
    def generate_signature(cls, message: str) -> str:
        """Generates standard HMAC-SHA256 signature for payload verification"""
        key = cls.GATEWAY_SECRET.encode('utf-8')
        msg = message.encode('utf-8')
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    @classmethod
    def validate_documents_ready_for_payment(cls, application: Application):
        """Require the current photo and identity uploads before collecting payment."""
        current_documents = application.get_current_documents()
        has_photo = any(
            document.document_type == 'Passport Photo'
            for document in current_documents
        )
        has_identity = any(
            any(
                label in (document.document_type or '').casefold()
                for label in ('citizenship', 'national id', 'nid')
            )
            for document in current_documents
        )
        rejected_documents = [
            document for document in current_documents
            if document.verification_status == 'Rejected'
        ]

        if not has_photo or not has_identity:
            raise ValueError(
                "Upload both a Passport Photo and a Citizenship Certificate or National ID before payment."
            )
        if rejected_documents:
            raise ValueError(
                "Replace every rejected current document before continuing the workflow."
            )
        return current_documents

    @classmethod
    @transaction.atomic
    def create_payment_request(
        cls,
        application: Application,
        applicant: Applicant,
        payment_type: str = "APPLICATION_FEE",
        gateway_name: str = "eSewa"
    ) -> Payment:
        """
        Initializes a payable request:
        1. Computes amount
        2. Generates unique reference
        3. Stores a pending gateway record
        4. Saves record in PostgreSQL
        5. Logs activity
        """
        application = Application.objects.select_for_update().get(
            application_id=application.application_id
        )

        verified = Payment.objects.select_for_update().filter(
            application=application,
            payment_type=payment_type,
        ).filter(
            Q(status='VERIFIED') | Q(payment_status='Completed')
        ).order_by('-verified_at', '-payment_id').first()
        if verified:
            return verified

        cls.validate_documents_ready_for_payment(application)

        # Never mutate a reference that may already have been submitted to eSewa.
        existing = Payment.objects.select_for_update().filter(
            application=application,
            payment_type=payment_type,
            status__in=['PENDING', 'QR_GENERATED', 'PAYMENT_INITIATED', 'PAID'],
        ).first()

        # Repeated button clicks and network retries must return the same
        # active request. Once a reference has been issued, replacing it could
        # leave the browser and server tracking different eSewa transactions.
        if existing and existing.payment_reference:
            return existing

        amount = cls.calculate_fee(application, payment_type)
        ref = cls.generate_payment_reference(application, payment_type)

        # A QR data URI is retained only for backward compatibility with older
        # tests and API consumers. The applicant UI uses the official signed
        # eSewa browser form, not this metadata QR.
        qr_dict = {
            "merchant_id": cls.MERCHANT_ID,
            "merchant_name": "Government of Nepal - Department of Passports",
            "payment_reference": ref,
            "application_id": application.application_id,
            "payment_type": payment_type,
            "amount": float(amount),
            "currency": "NPR",
            "gateway": gateway_name,
            "created_at": timezone.now().isoformat(),
            "environment": cls.ENVIRONMENT,
            "verify_url": f"/api/payments/status/{ref}/",
            "integration": "eSewa ePay v2",
        }
        qr_payload_str = json.dumps(qr_dict, separators=(',', ':'))

        # Generate Data URI SVG
        qr_code_uri = generate_qr_data_uri(qr_payload_str)

        if existing:
            # Update existing active request with new reference and fresh QR
            payment = existing
            payment.payment_reference = ref
            payment.amount = amount
            payment.gateway_name = gateway_name
            payment.payment_method = gateway_name if gateway_name in dict(Payment.METHOD_CHOICES) else 'eSewa'
            payment.status = "QR_GENERATED"
            payment.qr_code = qr_code_uri
            payment.qr_payload = qr_payload_str
            payment.save()
        else:
            payment = Payment.objects.create(
                application=application,
                applicant=applicant,
                payment_reference=ref,
                amount=amount,
                currency="NPR",
                payment_type=payment_type,
                gateway_name=gateway_name,
                payment_method=gateway_name if gateway_name in dict(Payment.METHOD_CHOICES) else 'eSewa',
                status="QR_GENERATED",
                qr_code=qr_code_uri,
                qr_payload=qr_payload_str,
                remarks=f"eSewa ePay request generated for {payment_type}"
            )

        # Record activity
        try:
            ActivityLog.objects.create(
                application=application,
                payment_reference=ref,
                action_taken=f"eSewa payment request generated: {ref} for NPR {amount:,.2f} ({payment_type})"
            )
        except Exception:
            pass

        return payment

    @classmethod
    def _mark_application_pending_for_final_review(cls, payment: Payment) -> bool:
        """Keep a paid application pending for document, biometric, and signature review."""
        application = Application.objects.select_for_update().get(
            application_id=payment.application_id
        )
        signature = getattr(application, 'digital_signature', None)
        already_finalized = bool(signature and signature.is_valid)
        if already_finalized:
            return False

        previous_status = application.status
        application.status = 'Pending'
        application.processing_notes = (
            'Payment verified. Awaiting staff document verification, biometric '
            'verification, and digital signature.'
        )
        application.save(update_fields=['status', 'processing_notes', 'last_updated'])
        try:
            ActivityLog.objects.create(
                application=application,
                payment_reference=payment.payment_reference,
                action_taken=(
                    f"Payment verified; application moved from {previous_status} to Pending "
                    "for document verification, biometrics, and digital signature"
                )[:255],
            )
        except Exception:
            pass
        return previous_status != 'Pending'

    @classmethod
    def fetch_esewa_status(cls, payment: Payment) -> dict:
        """Query eSewa's authoritative transaction status endpoint."""
        cls.validate_esewa_configuration()
        query = urlencode({
            'product_code': cls.MERCHANT_ID,
            'total_amount': cls.format_amount(payment.amount),
            'transaction_uuid': payment.payment_reference,
        })
        status_url = f"{cls.STATUS_URL}?{query}"
        request = Request(
            status_url,
            headers={'Accept': 'application/json', 'User-Agent': 'PassportQueue/1.0'},
            method='GET',
        )
        try:
            with urlopen(request, timeout=cls.HTTP_TIMEOUT) as response:
                body = response.read().decode('utf-8')
        except HTTPError as exc:
            raise ValueError(f"eSewa status service returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ValueError("eSewa status service is temporarily unavailable.") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("eSewa status service returned an invalid response.") from exc

        if not isinstance(payload, dict):
            raise ValueError("eSewa status service returned an invalid payload.")
        if payload.get('error_message'):
            raise ValueError(str(payload['error_message']))

        if str(payload.get('product_code')) != cls.MERCHANT_ID:
            raise ValueError("eSewa status product code does not match this merchant.")
        if str(payload.get('transaction_uuid')) != str(payment.payment_reference):
            raise ValueError("eSewa status transaction reference does not match.")
        try:
            status_amount = cls.normalize_amount(payload.get('total_amount'))
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise ValueError("eSewa status response contains an invalid amount.") from exc
        if status_amount != payment.amount:
            raise ValueError("eSewa status amount does not match the payment request.")

        return payload

    @classmethod
    @transaction.atomic
    def apply_esewa_status(cls, payment_id: int, status_payload: dict) -> tuple[bool, str, Payment]:
        """Atomically apply a validated eSewa status response to a payment."""
        payment = Payment.objects.select_for_update().get(payment_id=payment_id)
        if payment.status == 'VERIFIED':
            return True, "Payment is already verified and processed (idempotent)", payment

        gateway_status = str(status_payload.get('status') or '').upper()
        reference_id = status_payload.get('ref_id')

        if gateway_status == 'COMPLETE':
            if not reference_id:
                return False, "eSewa completed the payment without a reference ID.", payment
            if Payment.objects.exclude(pk=payment.pk).filter(
                transaction_id=str(reference_id)
            ).exists():
                return False, "This eSewa transaction ID has already been used.", payment

            now = timezone.now()
            payment.status = 'VERIFIED'
            payment.payment_status = 'Completed'
            payment.transaction_id = str(reference_id)
            payment.paid_at = payment.paid_at or now
            payment.verified_at = now
            payment.failure_reason = None
            payment.remarks = 'Verified through eSewa transaction status API'
            try:
                with transaction.atomic():
                    payment.save()
            except IntegrityError:
                payment.refresh_from_db()
                return False, "This eSewa transaction ID has already been used.", payment
            cls._mark_application_pending_for_final_review(payment)

            try:
                ActivityLog.objects.create(
                    application=payment.application,
                    payment_reference=payment.payment_reference,
                    action_taken=(
                        f"eSewa payment verified: {payment.payment_reference} "
                        f"NPR {payment.amount:,.2f} (Ref: {payment.transaction_id})"
                    ),
                )
            except Exception:
                pass

            try:
                Notification.objects.create(
                    applicant=payment.applicant,
                    application=payment.application,
                    type='Payment Verification',
                    message=(
                        f"Official receipt: eSewa fee payment of NPR {payment.amount:,.2f} "
                        f"for application #NP-{payment.application.application_id:04d} "
                        "has been verified. The application is now Pending for biometric "
                        "verification and digital signature."
                    ),
                    status='Unread',
                )
            except Exception:
                pass

            return True, "eSewa payment verified successfully.", payment

        if gateway_status in {'PENDING', 'AMBIGUOUS'}:
            payment.status = 'PAYMENT_INITIATED'
            payment.failure_reason = f"eSewa transaction is {gateway_status.lower()}; verification is pending."
            payment.save()
            return False, payment.failure_reason, payment

        if gateway_status == 'NOT_FOUND':
            payment.status = 'EXPIRED'
            payment.failure_reason = 'eSewa payment session expired or was not completed.'
        elif gateway_status in {'CANCELED', 'CANCELLED'}:
            payment.status = 'CANCELLED'
            payment.failure_reason = 'eSewa payment was cancelled or reversed.'
        elif gateway_status in {'FULL_REFUND', 'PARTIAL_REFUND'}:
            payment.status = 'FAILED'
            payment.failure_reason = f"eSewa reports the transaction as {gateway_status}."
        else:
            payment.status = 'FAILED'
            payment.failure_reason = f"Unrecognized eSewa transaction status: {gateway_status or 'missing'}."
        payment.save()
        return False, payment.failure_reason, payment

    @classmethod
    def verify_esewa_transaction(cls, payment: Payment) -> tuple[bool, str, Payment]:
        """Confirm a payment server-to-server before treating it as paid."""
        if payment.status == 'VERIFIED':
            return True, "Payment is already verified and processed (idempotent)", payment
        try:
            status_payload = cls.fetch_esewa_status(payment)
        except ValueError as exc:
            return False, str(exc), payment
        return cls.apply_esewa_status(payment.payment_id, status_payload)

    @classmethod
    def process_esewa_success(cls, encoded_data: str) -> tuple[bool, str, Payment]:
        """Validate eSewa's redirect response, then perform authoritative verification."""
        try:
            payload = cls.decode_and_verify_esewa_response(encoded_data)
        except ValueError as exc:
            return False, str(exc), None

        reference = str(payload['transaction_uuid'])
        with transaction.atomic():
            payment = Payment.objects.select_for_update().filter(
                payment_reference=reference
            ).first()
            if not payment:
                return False, "No payment request matches the eSewa transaction reference.", None
            if payment.status == 'VERIFIED':
                return True, "Payment is already verified and processed (idempotent)", payment
            if str(payload['product_code']) != cls.MERCHANT_ID:
                return False, "eSewa response product code does not match this merchant.", payment
            try:
                response_amount = cls.normalize_amount(payload['total_amount'])
            except (ValueError, TypeError, ArithmeticError):
                return False, "eSewa response contains an invalid amount.", payment
            if response_amount != payment.amount:
                return False, "eSewa response amount does not match the payment request.", payment
            if str(payload['status']).upper() != 'COMPLETE':
                return False, f"eSewa returned status {payload['status']}.", payment

            # A valid signed COMPLETE response means eSewa accepted the payment,
            # but the status API remains the final authority before workflow unlock.
            payment.status = 'PAID'
            payment.paid_at = payment.paid_at or timezone.now()
            payment.failure_reason = 'Signed eSewa response received; awaiting status verification.'
            payment.save()
        return cls.verify_esewa_transaction(payment)

    @classmethod
    @transaction.atomic
    def process_webhook(cls, payload: dict, signature: str = None) -> tuple[bool, str, Payment]:
        """
        Idempotent webhook processor.
        Verifies gateway signature, amount, transaction ID, and marks payment as VERIFIED.
        """
        ref = payload.get('payment_reference') or payload.get('order_id') or payload.get('transaction_uuid')
        txn_id = payload.get('transaction_id') or payload.get('ref_id') or payload.get('gateway_txn_id')
        amount_raw = payload.get('amount') or payload.get('total_amount')
        gateway_status = (payload.get('status') or payload.get('transaction_status') or '').upper()

        if not ref:
            return False, "Missing payment_reference in webhook payload", None

        # 1. Fetch Payment record from PostgreSQL with row lock
        payment = Payment.objects.select_for_update().filter(payment_reference=ref).first()
        if not payment:
            return False, f"Payment record not found for reference: {ref}", None

        # 2. Legacy callbacks are accepted only when signed. eSewa ePay itself
        # uses process_esewa_success(), which validates the documented Base64
        # response signature and then calls the status API.
        if not signature:
            return False, "Missing gateway signature", payment
        expected_sig = cls.generate_signature(f"{ref}|{amount_raw}|{txn_id}")
        if not hmac.compare_digest(signature, expected_sig):
            return False, "Invalid gateway signature", payment

        # 3. Require a real gateway transaction reference and a valid amount.
        if not txn_id:
            return False, "Missing gateway transaction ID", payment
        try:
            webhook_amount = Decimal(str(amount_raw))
        except (ValueError, TypeError):
            return False, "Invalid amount format in webhook", payment

        if webhook_amount != payment.amount:
            return False, f"Amount mismatch: Expected NPR {payment.amount}, received NPR {webhook_amount}", payment

        # 4. Check the gateway status before accepting idempotent retries.
        if gateway_status not in ['COMPLETE', 'SUCCESS', 'PAID', 'VERIFIED']:
            if payment.status == 'VERIFIED':
                return False, f"Gateway status failed: {gateway_status or 'missing'}", payment
            payment.status = "FAILED"
            payment.failure_reason = f"Gateway reported non-success status: {gateway_status or 'missing'}"
            payment.save()
            return False, f"Gateway status failed: {gateway_status or 'missing'}", payment

        # 5. A retry is idempotent only after all signed fields match the
        # already-verified record. Invalid callbacks never receive success.
        if payment.status == "VERIFIED":
            if str(payment.transaction_id) != str(txn_id):
                return False, "Verified payment transaction ID does not match", payment
            return True, "Payment is already verified and processed (idempotent)", payment

        if Payment.objects.exclude(pk=payment.pk).filter(
            transaction_id=str(txn_id)
        ).exists():
            return False, "Gateway transaction ID has already been used", payment

        # 6. Mark as VERIFIED atomically
        now = timezone.now()
        payment.status = "VERIFIED"
        payment.payment_status = "Completed"
        payment.transaction_id = str(txn_id)
        payment.paid_at = now
        payment.verified_at = now
        payment.failure_reason = None
        try:
            with transaction.atomic():
                payment.save()
        except IntegrityError:
            payment.refresh_from_db()
            return False, "Gateway transaction ID has already been used", payment
        cls._mark_application_pending_for_final_review(payment)

        # 7. Audit log & Citizen notification
        try:
            ActivityLog.objects.create(
                application=payment.application,
                payment_reference=ref,
                action_taken=f"Payment verified: {ref} NPR {payment.amount:,.2f} via {payment.gateway_name} (TXN: {payment.transaction_id})"
            )
        except Exception:
            pass

        try:
            Notification.objects.create(
                applicant=payment.applicant,
                application=payment.application,
                type="Payment Verification",
                message=(
                    f"Payment receipt: Fee of NPR {payment.amount:,.2f} for application "
                    f"#NP-{payment.application.application_id:04d} is verified. The application "
                    "is now Pending for biometric verification and digital signature."
                ),
                status="Unread"
            )
        except Exception:
            pass

        return True, "Payment verified successfully", payment

    @classmethod
    def simulate_sandbox_payment(cls, payment_reference: str) -> tuple[bool, str, Payment]:
        """
        DEVELOPMENT/SANDBOX PAYMENT SIMULATOR.
        ≠ REAL PRODUCTION PAYMENT.
        Creates a signed gateway callback to test end-to-end webhook verification
        without requiring live payment provider API access or actual currency.
        """
        payment = Payment.objects.filter(payment_reference=payment_reference).first()
        if not payment:
            return False, "Payment reference not found", None

        # Generate realistic transaction reference
        txn_id = f"TXN-{payment.gateway_name[:3].upper()}-{secrets.token_hex(4).upper()}-{int(time.time())}"
        payload = {
            "payment_reference": payment.payment_reference,
            "amount": str(payment.amount),
            "currency": "NPR",
            "transaction_id": txn_id,
            "status": "COMPLETE",
            "simulation": True,
            "environment": "DEVELOPMENT/SANDBOX PAYMENT ≠ REAL PRODUCTION PAYMENT"
        }
        # Compute valid signature
        sig = cls.generate_signature(f"{payment.payment_reference}|{payment.amount}|{txn_id}")
        return cls.process_webhook(payload, signature=sig)


# Backward-compatible alias
PaymentGatewayService = PaymentService
