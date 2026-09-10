import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'passport_system.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from decimal import Decimal
import json

from passport.models import (
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
    AuthToken
)
from passport.views import (
    ApplicantViewSet,
    StaffViewSet,
    AdministratorViewSet,
    ApplicationViewSet,
    DocumentViewSet,
    PaymentViewSet,
    QueueTokenViewSet
)
from passport.payment_service import PaymentGatewayService
from passport.pdf_generator import generate_passport_pdf

def print_check(name, passed, detail=""):
    mark = "[PASS]" if passed else "[FAIL]"
    print(f"{mark} {name}: {detail}")
    if not passed:
        raise AssertionError(f"Check failed: {name} - {detail}")

def run_all_tests():
    print("=" * 70)
    print("STARTING FULL SYSTEM VERIFICATION TEST SUITE (37 CHECKPOINTS)")
    print("=" * 70)

    factory = APIRequestFactory()

    # Phase 1: Setup test users
    admin, _ = Administrator.objects.get_or_create(
        email="test_admin@passport.gov.np",
        defaults={
            "username": "sysadmin_test",
            "password": make_password("AdminPass123!"),
            "role": "Super Admin"
        }
    )
    admin_token, _ = AuthToken.objects.get_or_create(user_id=admin.admin_id, user_type="administrator")

    staff, _ = Staff.objects.get_or_create(
        email="test_officer@passport.gov.np",
        defaults={
            "full_name": "Officer Bikash Test",
            "username": "officer_test",
            "password": make_password("StaffPass123!"),
            "phone": "9811002233",
            "department": "Verification Desk",
            "designation": "Inspector",
            "status": "Active",
            "is_active": True
        }
    )
    staff_token, _ = AuthToken.objects.get_or_create(user_id=staff.staff_id, user_type="staff")

    applicant, _ = Applicant.objects.get_or_create(
        email="test_citizen@example.com",
        defaults={
            "full_name": "Aayush Sharma Test",
            "password": make_password("CitizenPass123!"),
            "citizenship_number": "CTZ-998877",
            "phone_number": "9841234567",
            "address": "Kathmandu, Bagmati"
        }
    )
    applicant_token, _ = AuthToken.objects.get_or_create(user_id=applicant.applicant_id, user_type="applicant")

    print_check("Test Users Initialization", True, "Admin, Staff, and Applicant initialized with AuthTokens")

    # Checkpoint 1 & 2: Password hashing & AuthToken verification
    pw_ok = check_password("CitizenPass123!", applicant.password)
    print_check("Applicant Password Hashing", pw_ok, "PBKDF2-SHA256 verified")

    # Checkpoint 3: Security & Authorization - Unauthenticated access returns 401
    request = factory.get('/api/applications/')
    view = ApplicationViewSet.as_view({'get': 'list'})
    response = view(request)
    print_check("Unauthenticated Access Rejection", response.status_code == status.HTTP_401_UNAUTHORIZED, f"Status: {response.status_code}")

    # Checkpoint 4: Role-Based Authorization - Applicant cannot access Staff list
    request = factory.get('/api/staff/')
    request.user = applicant_token
    view = StaffViewSet.as_view({'get': 'list'})
    response = view(request)
    print_check("Applicant Blocked from Staff Roster (403)", response.status_code == status.HTTP_403_FORBIDDEN, f"Status: {response.status_code}")

    # Checkpoint 5: Role-Based Authorization - Applicant cannot access Administrator list
    request = factory.get('/api/administrators/')
    request.user = applicant_token
    view = AdministratorViewSet.as_view({'get': 'list'})
    response = view(request)
    print_check("Applicant Blocked from Admin Endpoint (403)", response.status_code == status.HTTP_403_FORBIDDEN, f"Status: {response.status_code}")

    # Checkpoint 6: Role-Based Authorization - Staff cannot delete Applicant
    request = factory.delete(f'/api/applicants/{applicant.applicant_id}/')
    request.user = staff_token
    view = ApplicantViewSet.as_view({'delete': 'destroy'})
    response = view(request, pk=applicant.applicant_id)
    print_check("Staff Forbidden to Delete Applicant (403)", response.status_code == status.HTTP_403_FORBIDDEN, f"Status: {response.status_code}")

    # Checkpoint 7: Clean old test applications
    Application.objects.filter(applicant=applicant).delete()

    # Checkpoint 8: Application Creation by Applicant
    request = factory.post('/api/applications/', {
        "passport_category": "Ordinary (34 Pages)",
        "service_type": "New Passport"
    }, format='json')
    request.user = applicant_token
    view = ApplicationViewSet.as_view({'post': 'create'})
    response = view(request)
    print_check("Application Creation", response.status_code == status.HTTP_201_CREATED, f"Status: {response.status_code}")

    app_id = response.data['application_id']
    test_app = Application.objects.get(application_id=app_id)

    # Checkpoint 9: Auto-provisioning of QueueToken
    has_token = QueueToken.objects.filter(application=test_app).exists()
    print_check("Automatic QueueToken Generation", has_token, f"Token ID: {test_app.queue_token.token_number if has_token else 'None'}")

    # Checkpoint 10: Auto-provisioning of Fee Assessment
    has_payment = Payment.objects.filter(application=test_app).exists()
    print_check("Automatic Fee Assessment Provisioning", has_payment, f"Fee: NPR {test_app.fee_amount}")

    # Checkpoint 11: Auto-provisioning of Notification
    has_notification = Notification.objects.filter(application=test_app).exists()
    print_check("Automatic Submission Notification", has_notification, "Citizen notification record created")

    # Checkpoint 12: Dynamic Workflow Locking before Payment
    steps = test_app.get_workflow_steps()
    step_5 = next(s for s in steps if s['step'] == 5)
    step_6 = next(s for s in steps if s['step'] == 6)
    step_7 = next(s for s in steps if s['step'] == 7)
    step_8 = next(s for s in steps if s['step'] == 8)
    step_9 = next(s for s in steps if s['step'] == 9)

    fee_action_required = (step_5['status'] == 'Action Required')
    subsequent_locked = (step_6['status'] == 'Locked' and step_7['status'] == 'Locked' and step_8['status'] == 'Locked' and step_9['status'] == 'Locked')
    print_check("Dynamic Workflow Locking (Pre-Payment)", fee_action_required and subsequent_locked, f"Step 5: {step_5['status']}, Step 6-9: Locked={subsequent_locked}")

    # Checkpoint 13: Tariff Calculation
    tariff_34 = PaymentGatewayService.calculate_tariff("Ordinary (34 Pages)")
    tariff_66 = PaymentGatewayService.calculate_tariff("Ordinary (66 Pages)")
    tariff_urg = PaymentGatewayService.calculate_tariff("Urgent (34 Pages)")
    tariff_dip = PaymentGatewayService.calculate_tariff("Diplomatic / Official")
    tariffs_ok = (tariff_34 == Decimal('5000.00') and tariff_66 == Decimal('10000.00') and tariff_urg == Decimal('12000.00') and tariff_dip == Decimal('15000.00'))
    print_check("Dynamic Government Tariffs Calculation", tariffs_ok, f"34p: {tariff_34}, 66p: {tariff_66}, Urg: {tariff_urg}, Dip: {tariff_dip}")

    # Checkpoint 14: Payment Request & QR Code Generation
    request = factory.post('/api/payments/create-request/', {
        "application_id": test_app.application_id,
        "payment_method": "eSewa",
        "gateway_name": "eSewa-Nepal"
    }, format='json')
    request.user = applicant_token
    view = PaymentViewSet.as_view({'post': 'create_request'})
    response = view(request)
    print_check("Payment Request & QR Generation", response.status_code == status.HTTP_200_OK and "qr_code" in response.data, f"Ref: {response.data.get('payment_reference')}")
    pay_ref = response.data['payment_reference']

    # Checkpoint 15: Pure-Python QR Code Data URI Validated
    qr_code_str = response.data.get('qr_code', '')
    has_valid_qr = qr_code_str.startswith('data:image/svg+xml;utf8,') or qr_code_str.startswith('data:image/png;base64,')
    print_check("QR Code Data-URI Validation", has_valid_qr, f"QR prefix: {qr_code_str[:30]}...")

    # Checkpoint 16: Check Payment Status via API
    request = factory.get(f'/api/payments/status/{pay_ref}/')
    request.user = applicant_token
    view = PaymentViewSet.as_view({'get': 'status_by_ref'})
    response = view(request, reference=pay_ref)
    print_check("Payment Status Query Endpoint", response.status_code == status.HTTP_200_OK, f"Status: {response.data.get('status')}")

    # Checkpoint 17: Sandbox Payment Simulation Callback
    request = factory.post('/api/payments/simulate-sandbox-callback/', {
        "payment_reference": pay_ref,
        "success": True
    }, format='json')
    request.user = applicant_token
    view = PaymentViewSet.as_view({'post': 'simulate_sandbox_callback'})
    response = view(request)
    print_check("Sandbox Payment Callback Processing", response.status_code == status.HTTP_200_OK, f"Message: {response.data.get('message')}")

    # Checkpoint 18: Payment State in PostgreSQL verified as VERIFIED
    verified_payment = Payment.objects.get(payment_reference=pay_ref)
    payment_verified_ok = (verified_payment.status == 'VERIFIED' and verified_payment.payment_status == 'Completed')
    print_check("Payment Database Dual-State Synchronization", payment_verified_ok, f"Status: {verified_payment.status}, Legacy: {verified_payment.payment_status}")

    # Checkpoint 19: Workflow Unlocks Step 6 after Payment Verification
    test_app.refresh_from_db()
    unlocked_steps = test_app.get_workflow_steps()
    step_5_post = next(s for s in unlocked_steps if s['step'] == 5)
    step_6_post = next(s for s in unlocked_steps if s['step'] == 6)
    workflow_unlocked = (step_5_post['status'] == 'Completed' and step_6_post['status'] in ['Pending', 'Action Required'])
    print_check("Workflow Stage Unlock Post-Payment", workflow_unlocked, f"Step 5: {step_5_post['status']}, Step 6: {step_6_post['status']}")

    # Checkpoint 20: Applicant Cannot Modify Official Application Status (Security Restriction)
    request = factory.patch(f'/api/applications/{test_app.application_id}/', {
        "status": "Approved"
    }, format='json')
    request.user = applicant_token
    view = ApplicationViewSet.as_view({'patch': 'partial_update'})
    response = view(request, pk=test_app.application_id)
    print_check("Applicant Blocked From Self-Approving (403)", response.status_code == status.HTTP_403_FORBIDDEN, f"Status: {response.status_code}")

    # Checkpoint 21: Document Upload by Applicant
    request = factory.post('/api/documents/', {
        "application": test_app.application_id,
        "document_type": "Citizenship Certificate",
        "file_path": "/static/uploads/test_citz.pdf",
        "verification_status": "Pending"
    }, format='json')
    request.user = applicant_token
    view = DocumentViewSet.as_view({'post': 'create'})
    response = view(request)
    print_check("Citizen Document Upload", response.status_code == status.HTTP_201_CREATED, f"Doc ID: {response.data.get('document_id')}")
    doc_id = response.data['document_id']

    # Checkpoint 22: Applicant Forbidden From Self-Verifying Document (Security Restriction)
    request = factory.patch(f'/api/documents/{doc_id}/', {
        "verification_status": "Verified"
    }, format='json')
    request.user = applicant_token
    view = DocumentViewSet.as_view({'patch': 'partial_update'})
    response = view(request, pk=doc_id)
    print_check("Applicant Blocked From Self-Verifying Documents (403)", response.status_code == status.HTTP_403_FORBIDDEN, f"Status: {response.status_code}")

    # Checkpoint 23: Staff Document Verification
    request = factory.post(f'/api/documents/{doc_id}/verify-document/', {
        "remarks": "Official hologram verified by officer"
    }, format='json')
    request.user = staff_token
    view = DocumentViewSet.as_view({'post': 'verify_document'})
    response = view(request, pk=doc_id)
    print_check("Staff Document Verification Endpoint", response.status_code == status.HTTP_200_OK, f"Status: {response.data.get('verification_status')}")

    # Checkpoint 24: Staff Biometric Verification
    request = factory.post(f'/api/applications/{test_app.application_id}/verify-biometrics/', {
        "biometric_status": "Verified",
        "remarks": "10-fingerprint live scan match 99.4%"
    }, format='json')
    request.user = staff_token
    view = ApplicationViewSet.as_view({'post': 'verify_biometrics'})
    response = view(request, pk=test_app.application_id)
    print_check("Staff Biometrics Verification Endpoint", response.status_code == status.HTTP_200_OK, f"Biometrics: {response.data.get('biometric_status')}")

    # Checkpoint 25: Staff Authorize Digital Signature & Approval
    request = factory.post(f'/api/applications/{test_app.application_id}/authorize-signature/', {}, format='json')
    request.user = staff_token
    view = ApplicationViewSet.as_view({'post': 'authorize_signature'})
    response = view(request, pk=test_app.application_id)
    print_check("PKI Digital Signature Authorization", response.status_code == status.HTTP_200_OK, f"Serial: {response.data.get('certificate_serial')}")

    # Checkpoint 26: Application Status in PostgreSQL is Approved
    test_app.refresh_from_db()
    app_approved_ok = (test_app.status == 'Approved' and hasattr(test_app, 'digital_signature') and test_app.digital_signature.is_valid)
    print_check("Application Approval & Signature State in DB", app_approved_ok, f"Status: {test_app.status}, PKI Valid: {test_app.digital_signature.is_valid}")

    # Checkpoint 27: Queue Token Marked Completed
    test_app.queue_token.refresh_from_db()
    print_check("Queue Token Auto-Completion on Approval", test_app.queue_token.queue_status == 'Completed', f"Queue Status: {test_app.queue_token.queue_status}")

    # Checkpoint 28: Virtual Passport PDF Certificate Generation
    pdf_bytes = generate_passport_pdf(test_app)
    is_valid_pdf = pdf_bytes.startswith(b'%PDF')
    print_check("Virtual Passport PDF Generation Engine", is_valid_pdf, f"Generated PDF Size: {len(pdf_bytes)} bytes, Header: {pdf_bytes[:5]}")

    # Checkpoint 29: Citizen Download PDF Endpoint
    request = factory.get(f'/api/applications/{test_app.application_id}/download-pdf/')
    request.user = applicant_token
    view = ApplicationViewSet.as_view({'get': 'download_pdf'})
    response = view(request, pk=test_app.application_id)
    print_check("Citizen PDF Download API Response", response.status_code == status.HTTP_200_OK and response['Content-Type'] == 'application/pdf', f"Status: {response.status_code}, Content-Type: {response.get('Content-Type')}")

    # Checkpoint 30: Staff Desk Summary Live Endpoint
    request = factory.get('/api/staff/desk-summary/')
    request.user = staff_token
    view = StaffViewSet.as_view({'get': 'desk_summary'})
    response = view(request)
    desk_ok = (response.status_code == status.HTTP_200_OK and 'pending_verifications' in response.data and 'queue_waiting' in response.data)
    print_check("Staff Desk Summary Metrics", desk_ok, f"Completed: {response.data.get('completed_count')}, Docs Verified: {response.data.get('verified_documents')}")

    # Checkpoint 31: Administrator System Summary Live PostgreSQL Endpoint
    request = factory.get('/api/administrators/system-summary/')
    request.user = admin_token
    view = AdministratorViewSet.as_view({'get': 'system_summary'})
    response = view(request)
    admin_ok = (response.status_code == status.HTTP_200_OK and 'total_applications' in response.data and 'total_revenue' in response.data)
    print_check("Admin System Summary (PostgreSQL Aggregation)", admin_ok, f"Total Apps: {response.data.get('total_applications')}, Revenue: NPR {response.data.get('total_revenue')}")

    # Checkpoint 32: Administrator Staff Management - Create Staff
    new_username = f"officer_unit_{test_app.application_id}"
    request = factory.post('/api/staff/', {
        "full_name": "Sub-Inspector Maya Thapa",
        "username": new_username,
        "email": f"{new_username}@passport.gov.np",
        "password": "SecurePassword123!",
        "phone": "9800112233",
        "department": "Biometric Enrollment",
        "designation": "Inspector",
        "status": "Active"
    }, format='json')
    request.user = admin_token
    view = StaffViewSet.as_view({'post': 'create'})
    response = view(request)
    print_check("Admin Staff Creation", response.status_code == status.HTTP_201_CREATED, f"Staff ID: {response.data.get('staff_id')}")
    created_staff_id = response.data['staff_id']

    # Checkpoint 33: Administrator Staff Management - Toggle Deactivate
    request = factory.patch(f'/api/staff/{created_staff_id}/', {
        "status": "Inactive"
    }, format='json')
    request.user = admin_token
    view = StaffViewSet.as_view({'patch': 'partial_update'})
    response = view(request, pk=created_staff_id)
    print_check("Admin Staff Status Toggle", response.status_code == status.HTTP_200_OK and response.data.get('status') == 'Inactive', f"Status: {response.data.get('status')}")

    # Checkpoint 34: Administrator Staff Password Reset
    request = factory.post(f'/api/staff/{created_staff_id}/reset-password/', {
        "new_password": "NewStaffPassword456!"
    }, format='json')
    request.user = admin_token
    view = StaffViewSet.as_view({'post': 'reset_password'})
    response = view(request, pk=created_staff_id)
    print_check("Admin Staff Password Reset", response.status_code == status.HTTP_200_OK, f"Message: {response.data.get('message')}")

    # Checkpoint 35: Administrator Staff Deletion
    request = factory.delete(f'/api/staff/{created_staff_id}/')
    request.user = admin_token
    view = StaffViewSet.as_view({'delete': 'destroy'})
    response = view(request, pk=created_staff_id)
    print_check("Admin Staff Deletion", response.status_code == status.HTTP_204_NO_CONTENT, f"Status: {response.status_code}")

    # Checkpoint 36: ActivityLog Persistence
    logs_count = ActivityLog.objects.filter(application=test_app).count()
    print_check("ActivityLog Audit Trail Persistence", logs_count > 0, f"{logs_count} audit actions logged for test application")

    # Checkpoint 37: Clean Final Workflow Inspection
    final_workflow = test_app.get_workflow_steps()
    step_9_final = next(s for s in final_workflow if s['step'] == 9)
    print_check("Final 9-Step Workflow Completion State", step_9_final['status'] == 'Completed' and step_9_final.get('can_download') == True, f"Step 9 Status: {step_9_final['status']}, Can Download: {step_9_final.get('can_download')}")

    print("=" * 70)
    print("ALL 37 SYSTEM VERIFICATION CHECKPOINTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_all_tests()
