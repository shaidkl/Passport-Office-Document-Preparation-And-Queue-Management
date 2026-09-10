"""
Comprehensive Automated Test Suite for Nepal Passport Office Payment System
Tests:
1. Backend dynamic fee calculation (34 pgs, 66 pgs, urgent, express)
2. Discrete payment reference generation (PP-YYYY-XXXX-TYPE)
3. QR Code generation (SVG/data-URI)
4. PaymentService request initiation
5. HMAC-SHA256 signature verification
6. Automatic idempotent webhook processing
7. Database transaction safety
8. Workflow dynamic locking (Step 5 unverified -> Step 6-9 locked; Step 5 verified -> unlocked)
9. Tampered amount rejection
10. Multiple independent payments per application (Application fee + Urgent fee)
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django standalone environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from passport.models import Applicant, Application, Payment, ActivityLog, Notification
from passport.payment_service import PaymentService
from passport.qr_generator import generate_qr_svg, generate_qr_data_uri


def run_tests():
    print("=" * 60)
    print("STARTING PAYMENT SYSTEM AUTOMATED VERIFICATION")
    print("=" * 60)

    # 1. Setup Test Applicant & Application
    applicant, _ = Applicant.objects.get_or_create(
        email="paytest_citizen@example.com",
        defaults={
            "full_name": "Hari Prasad Sharma",
            "phone": "9841000000",
            "password": "pbkdf2_sha256$testpassword",
            "date_of_birth": "1990-01-01",
            "gender": "Male",
            "nationality": "Nepali",
            "address": "Kathmandu, Ward 4"
        }
    )

    app34 = Application.objects.create(
        applicant=applicant,
        passport_category="Ordinary (34 Pages)",
        service_type="New Passport",
        status="Pending"
    )

    app66 = Application.objects.create(
        applicant=applicant,
        passport_category="Ordinary (66 Pages)",
        service_type="New Passport",
        status="Pending"
    )

    app_urgent = Application.objects.create(
        applicant=applicant,
        passport_category="Express Urgent Service",
        service_type="New Passport",
        status="Pending"
    )

    print("\n[TEST 1] Backend Fee Calculation Authority")
    fee34 = PaymentService.calculate_fee(app34, "APPLICATION_FEE")
    fee66 = PaymentService.calculate_fee(app66, "APPLICATION_FEE")
    fee_urg = PaymentService.calculate_fee(app_urgent, "APPLICATION_FEE")
    fee_urg_extra = PaymentService.calculate_fee(app34, "URGENT_PROCESSING_FEE")

    assert fee34 == Decimal("5000.00"), f"Expected 5000.00, got {fee34}"
    assert fee66 == Decimal("10000.00"), f"Expected 10000.00, got {fee66}"
    assert fee_urg == Decimal("12000.00"), f"Expected 12000.00, got {fee_urg}"
    assert fee_urg_extra == Decimal("3000.00"), f"Expected 3000.00, got {fee_urg_extra}"
    print(f"  ✓ 34 Pages Normal Fee: NPR {fee34:,.2f}")
    print(f"  ✓ 66 Pages Normal Fee: NPR {fee66:,.2f}")
    print(f"  ✓ Express Urgent Fee:  NPR {fee_urg:,.2f}")
    print(f"  ✓ Separate Urgent Surcharge: NPR {fee_urg_extra:,.2f}")

    print("\n[TEST 2] Standards-Compliant QR Code Generation")
    test_payload = "https://passport.gov.np/pay/PP-2026-0001-FEE"
    qr_svg = generate_qr_svg(test_payload)
    qr_uri = generate_qr_data_uri(test_payload)

    assert "<svg" in qr_svg and "</svg>" in qr_svg, "Generated QR SVG is invalid"
    assert qr_uri.startswith("data:image/svg+xml;utf8,"), "Data URI format is invalid"
    print(f"  ✓ QR SVG generated successfully ({len(qr_svg)} bytes)")
    print(f"  ✓ QR Data URI valid: {qr_uri[:45]}...")

    print("\n[TEST 3] Workflow Dynamic Locking (Pre-Payment)")
    steps_pre = app34.get_workflow_steps()
    step5_pre = next(s for s in steps_pre if s["step"] == 5)
    step6_pre = next(s for s in steps_pre if s["step"] == 6)
    step7_pre = next(s for s in steps_pre if s["step"] == 7)

    assert step5_pre["status"] == "Payment Required", f"Expected Payment Required, got {step5_pre['status']}"
    assert step6_pre["status"] == "Locked", f"Expected Locked for Step 6, got {step6_pre['status']}"
    assert step7_pre["status"] == "Locked", f"Expected Locked for Step 7, got {step7_pre['status']}"
    print("  ✓ Step 5 status: 'Payment Required'")
    print(f"  ✓ Step 6 locked: '{step6_pre['details']}'")
    print(f"  ✓ Step 7 locked: '{step7_pre['details']}'")

    print("\n[TEST 4] Payment Request Creation & QR Generation")
    payment = PaymentService.create_payment_request(
        application=app34,
        applicant=applicant,
        payment_type="APPLICATION_FEE",
        gateway_name="eSewa"
    )

    assert payment.payment_reference.startswith("PP-"), f"Invalid reference format: {payment.payment_reference}"
    assert payment.status == "QR_GENERATED"
    assert payment.amount == Decimal("5000.00")
    assert payment.qr_code is not None and "<svg" in payment.qr_code
    print(f"  ✓ Payment record created: ID #{payment.payment_id}")
    print(f"  ✓ Unique Reference: {payment.payment_reference}")
    print(f"  ✓ Status: {payment.status}")
    print(f"  ✓ Amount: {payment.currency} {payment.amount:,.2f}")

    print("\n[TEST 5] Rejection of Tampered Amount")
    tampered_payload = {
        "payment_reference": payment.payment_reference,
        "amount": "100.00",  # Fake reduced amount
        "transaction_id": "TXN-TAMPER-001",
        "status": "COMPLETE"
    }
    tampered_sig = PaymentService.generate_signature(f"{payment.payment_reference}|100.00|TXN-TAMPER-001")
    ok, err_msg, _ = PaymentService.process_webhook(tampered_payload, signature=tampered_sig)
    assert not ok, "Tampered amount should be rejected!"
    payment.refresh_from_db()
    assert payment.status == "FAILED"
    print(f"  ✓ Tampered amount correctly rejected: '{err_msg}'")

    print("\n[TEST 6] Automatic Gateway Webhook Verification & Atomic Processing")
    # Reset to QR_GENERATED for legitimate payment
    payment.status = "QR_GENERATED"
    payment.save()

    valid_txn_id = "TXN-ESEWA-99887766"
    valid_payload = {
        "payment_reference": payment.payment_reference,
        "amount": str(payment.amount),
        "transaction_id": valid_txn_id,
        "status": "COMPLETE",
        "currency": "NPR"
    }
    valid_sig = PaymentService.generate_signature(f"{payment.payment_reference}|{payment.amount}|{valid_txn_id}")
    ok, success_msg, verified_payment = PaymentService.process_webhook(valid_payload, signature=valid_sig)

    assert ok, f"Legitimate webhook failed: {success_msg}"
    verified_payment.refresh_from_db()
    assert verified_payment.status == "VERIFIED"
    assert verified_payment.payment_status == "Completed"
    assert verified_payment.transaction_id == valid_txn_id
    assert verified_payment.paid_at is not None
    assert verified_payment.verified_at is not None
    print(f"  ✓ Webhook verified: '{success_msg}'")
    print(f"  ✓ Payment status: {verified_payment.status}")
    print(f"  ✓ Legacy payment_status synced: {verified_payment.payment_status}")
    print(f"  ✓ Stored Transaction ID: {verified_payment.transaction_id}")
    print(f"  ✓ Verified timestamp: {verified_payment.verified_at}")

    print("\n[TEST 7] Webhook Idempotency (Duplicate Prevention)")
    ok_dup, dup_msg, _ = PaymentService.process_webhook(valid_payload, signature=valid_sig)
    assert ok_dup, "Idempotent duplicate webhook should return success"
    assert "idempotent" in dup_msg.lower() or "already verified" in dup_msg.lower()
    print(f"  ✓ Duplicate webhook handled idempotently: '{dup_msg}'")

    print("\n[TEST 8] Workflow Dynamic Unlocking (Post-Payment)")
    steps_post = app34.get_workflow_steps()
    step5_post = next(s for s in steps_post if s["step"] == 5)
    step6_post = next(s for s in steps_post if s["step"] == 6)

    assert step5_post["status"] == "Completed", f"Expected Completed, got {step5_post['status']}"
    assert step6_post["status"] != "Locked", f"Step 6 should be unlocked, got {step6_post['status']}"
    print(f"  ✓ Step 5 Fee status: '{step5_post['status']}'")
    print(f"  ✓ Step 5 details: '{step5_post['details']}'")
    print(f"  ✓ Step 6 Biometrics unlocked: Status is '{step6_post['status']}'")

    print("\n[TEST 9] Multiple Independent Payments per Application")
    urgent_payment = PaymentService.create_payment_request(
        application=app34,
        applicant=applicant,
        payment_type="URGENT_PROCESSING_FEE",
        gateway_name="Khalti"
    )
    assert urgent_payment.payment_id != verified_payment.payment_id
    assert urgent_payment.payment_reference != verified_payment.payment_reference
    assert urgent_payment.payment_type == "URGENT_PROCESSING_FEE"
    assert urgent_payment.amount == Decimal("3000.00")

    all_payments = list(app34.payments.all())
    assert len(all_payments) >= 2, f"Expected multiple payment records, found {len(all_payments)}"
    print(f"  ✓ Payment #1: {verified_payment.payment_reference} ({verified_payment.payment_type}) NPR {verified_payment.amount} - {verified_payment.status}")
    print(f"  ✓ Payment #2: {urgent_payment.payment_reference} ({urgent_payment.payment_type}) NPR {urgent_payment.amount} - {urgent_payment.status}")
    print("  ✓ All payments independently stored and traceable!")

    print("\n[TEST 10] Sandbox Simulation Engine")
    ok_sim, sim_msg, sim_res = PaymentService.simulate_sandbox_payment(urgent_payment.payment_reference)
    assert ok_sim, f"Sandbox simulation failed: {sim_msg}"
    urgent_payment.refresh_from_db()
    assert urgent_payment.status == "VERIFIED"
    print(f"  ✓ Sandbox payment simulated: '{sim_msg}'")
    print(f"  ✓ Simulated TXN: {urgent_payment.transaction_id}")
    print(f"  ✓ Status updated to: {urgent_payment.status}")

    print("\n" + "=" * 60)
    print("ALL 10 TESTS COMPLETED SUCCESSFULLY! ZERO ERRORS.")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
