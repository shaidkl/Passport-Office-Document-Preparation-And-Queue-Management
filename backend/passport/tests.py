import re
from datetime import timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .authentication import CustomUser
from .digital_signature_service import sign_application, verify_signature
from .models import (
    ActivityLog, Administrator, Applicant, Application, AuthToken,
    DigitalSignature, Document, Notification, Payment, QueueToken, Staff,
)
from .payment_service import PaymentService
from .passport_number_service import assign_passport_number
from .pdf_generator import build_td3_mrz
from .upload_security import UploadSecurityError, validate_uploaded_document


class DocumentDecisionTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Document Test Citizen',
            email='document-citizen@example.com',
            phone='9812345678',
            password='TestPass!8472',
            date_of_birth='1995-01-01',
            gender='Other',
            nationality='Nepali',
            address='Kathmandu',
        )
        self.staff = Staff.objects.create(
            full_name='Document Test Officer',
            username='document_test_officer',
            email='document-officer@example.com',
            phone='9800000001',
            password='TestPass!8472',
        )
        self.application = Application.objects.create(applicant=self.applicant)
        Payment.objects.create(
            application=self.application,
            applicant=self.applicant,
            payment_reference='TEST-DOCUMENT-PAYMENT',
            transaction_id='TEST-DOCUMENT-TXN',
            amount=self.application.fee_amount,
            status='VERIFIED',
            payment_status='Completed',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=CustomUser(self.staff, 'staff'))

    def create_document(self, status='Pending', inspected=False, suffix='original'):
        return Document.objects.create(
            application=self.application,
            document_type='Citizenship Certificate',
            file_name=f'citizenship-{suffix}.pdf',
            file_path=SimpleUploadedFile(
                f'citizenship-{suffix}.pdf',
                b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF',
                content_type='application/pdf',
            ),
            verification_status=status,
            rejection_reason='Original rejection' if status == 'Rejected' else '',
            is_inspected=inspected,
        )

    def test_pending_can_be_rejected_but_rejected_cannot_be_verified(self):
        Document.objects.create(
            application=self.application,
            document_type='Passport Photo',
            file_name='approved-photo.jpg',
            file_path=SimpleUploadedFile(
                'approved-photo.jpg',
                b'approved-photo',
                content_type='image/jpeg',
            ),
            verification_status='Verified',
            is_inspected=True,
        )
        document = self.create_document()

        rejected = self.client.post(
            f'/api/documents/{document.document_id}/reject-document/',
            {'application_id': self.application.application_id, 'reason': 'Unreadable scan'},
            format='json',
        )
        self.assertEqual(rejected.status_code, 200)

        verify_after_reject = self.client.post(
            f'/api/documents/{document.document_id}/verify-document/',
            {'application_id': self.application.application_id},
            format='json',
        )
        self.assertEqual(verify_after_reject.status_code, 400)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, 'Rejected')
        self.assertEqual(document.rejection_reason, 'Unreadable scan')
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'Rejected')
        self.assertEqual(rejected.data['application_status'], 'Rejected')

    def test_pending_inspected_document_can_be_verified_but_not_rejected_afterward(self):
        document = self.create_document(inspected=True)

        verified = self.client.post(
            f'/api/documents/{document.document_id}/verify-document/',
            {'application_id': self.application.application_id},
            format='json',
        )
        self.assertEqual(verified.status_code, 200)

        duplicate_verify = self.client.post(
            f'/api/documents/{document.document_id}/verify-document/',
            {'application_id': self.application.application_id},
            format='json',
        )
        self.assertEqual(duplicate_verify.status_code, 400)

        reject_after_verify = self.client.post(
            f'/api/documents/{document.document_id}/reject-document/',
            {'application_id': self.application.application_id, 'reason': 'Second decision'},
            format='json',
        )
        self.assertEqual(reject_after_verify.status_code, 400)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, 'Verified')

    def test_pending_document_cannot_be_verified_before_inspection(self):
        document = self.create_document(inspected=False)
        response = self.client.post(
            f'/api/documents/{document.document_id}/verify-document/',
            {'application_id': self.application.application_id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, 'Pending')

    def test_final_document_record_cannot_be_edited_or_deleted(self):
        document = self.create_document(status='Rejected')

        patch_response = self.client.patch(
            f'/api/documents/{document.document_id}/',
            {'verification_status': 'Verified'},
            format='json',
        )
        delete_response = self.client.delete(f'/api/documents/{document.document_id}/')

        self.assertEqual(patch_response.status_code, 405)
        self.assertEqual(delete_response.status_code, 405)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, 'Rejected')

    def test_replacement_upload_keeps_rejected_history_and_blocks_duplicate_pending_upload(self):
        rejected_document = self.create_document(status='Rejected')
        self.application.status = 'Rejected'
        self.application.save(update_fields=['status'])
        old_file_name = rejected_document.file_path.name
        self.client.force_authenticate(user=CustomUser(self.applicant, 'applicant'))

        replacement_payload = {
            'application': str(self.application.application_id),
            'document_type': 'Citizenship Certificate',
            'file_name': 'citizenship-replacement.pdf',
            'file_path': SimpleUploadedFile(
                'citizenship-replacement.pdf',
                b'%PDF-1.4\n2 0 obj\n<<>>\nendobj\n%%EOF',
                content_type='application/pdf',
            ),
        }
        replacement = self.client.post('/api/documents/', replacement_payload, format='multipart')
        self.assertEqual(replacement.status_code, 201)

        rejected_document.refresh_from_db()
        self.assertEqual(rejected_document.verification_status, 'Rejected')
        self.assertTrue(rejected_document.file_path.storage.exists(old_file_name))
        self.assertEqual(
            Document.objects.filter(
                application=self.application,
                document_type='Citizenship Certificate',
            ).count(),
            2,
        )
        self.assertEqual(self.application.get_current_documents()[0].verification_status, 'Pending')
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'Pending')
        self.assertEqual(replacement.data['application_status'], 'Pending')

        duplicate_payload = {
            'application': str(self.application.application_id),
            'document_type': 'Citizenship Certificate',
            'file_name': 'duplicate.pdf',
            'file_path': SimpleUploadedFile(
                'duplicate.pdf',
                b'%PDF-1.4\n3 0 obj\n<<>>\nendobj\n%%EOF',
                content_type='application/pdf',
            ),
        }
        duplicate = self.client.post('/api/documents/', duplicate_payload, format='multipart')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(
            Document.objects.filter(
                application=self.application,
                document_type='Citizenship Certificate',
            ).count(),
            2,
        )

    def test_application_stays_rejected_until_every_rejected_type_is_replaced(self):
        self.create_document(status='Rejected', suffix='rejected-citizenship')
        Document.objects.create(
            application=self.application,
            document_type='Passport Photo',
            file_name='rejected-photo.jpg',
            file_path=SimpleUploadedFile(
                'rejected-photo.jpg',
                b'rejected-photo',
                content_type='image/jpeg',
            ),
            verification_status='Rejected',
            rejection_reason='Photo background is invalid',
            is_inspected=True,
        )
        self.application.status = 'Rejected'
        self.application.save(update_fields=['status'])
        self.client.force_authenticate(user=CustomUser(self.applicant, 'applicant'))

        response = self.client.post(
            '/api/documents/',
            {
                'application': str(self.application.application_id),
                'document_type': 'Citizenship Certificate',
                'file_name': 'citizenship-replacement.pdf',
                'file_path': SimpleUploadedFile(
                    'citizenship-replacement.pdf',
                    b'%PDF-1.4\nreplacement\n%%EOF',
                    content_type='application/pdf',
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'Rejected')
        self.assertEqual(response.data['application_status'], 'Rejected')

    def test_verified_replacement_keeps_history_but_cannot_bypass_final_workflow(self):
        rejected_document = self.create_document(status='Rejected', suffix='rejected-history')
        replacement = self.create_document(status='Verified', inspected=True, suffix='verified-replacement')
        Document.objects.create(
            application=self.application,
            document_type='Passport Photo',
            file_name='verified-photo.jpg',
            file_path=SimpleUploadedFile(
                'verified-photo.jpg',
                b'\xff\xd8\xff\xe0' + (b'passport-photo' * 128) + b'\xff\xd9',
                content_type='image/jpeg',
            ),
            verification_status='Verified',
            is_inspected=True,
        )

        response = self.client.patch(
            f'/api/applications/{self.application.application_id}/',
            {'status': 'Approved'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.application.refresh_from_db()
        rejected_document.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(self.application.status, 'Pending')
        self.assertEqual(rejected_document.verification_status, 'Rejected')
        self.assertEqual(replacement.verification_status, 'Verified')


class PortalLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = 'PortalPass!8472'
        self.applicant = Applicant.objects.create(
            full_name='Portal Test Citizen',
            email='portal-citizen@example.com',
            phone='9812345680',
            password=self.password,
            date_of_birth='1995-01-01',
            gender='Other',
            nationality='Nepali',
            address='Kathmandu',
        )
        self.staff = Staff.objects.create(
            full_name='Portal Test Officer',
            username='portal_test_officer',
            email='portal-staff@example.com',
            phone='9812345681',
            password=self.password,
        )
        self.administrator = Administrator.objects.create(
            full_name='Portal Test Administrator',
            username='portal_test_admin',
            email='portal-admin@example.com',
            phone='9812345682',
            password=self.password,
        )

    def test_each_login_url_renders_its_role_specific_page(self):
        cases = (
            ('/login/', 'citizen'),
            ('/staff/login/', 'staff'),
            ('/admin-portal/login/', 'administrator'),
        )
        for url, portal_role in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'data-portal-role="{portal_role}"')

    def test_each_account_can_use_its_own_portal(self):
        cases = (
            ('portal-citizen@example.com', 'citizen', 'citizen'),
            ('portal_test_officer', 'staff', 'staff'),
            ('portal_test_admin', 'administrator', 'administrator'),
        )
        for identifier, portal_role, expected_role in cases:
            with self.subTest(portal_role=portal_role):
                response = self.client.post(
                    '/api/login/',
                    {
                        'email': identifier,
                        'password': self.password,
                        'portal_role': portal_role,
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['role'], expected_role)
                self.assertNotIn('token', response.data)
                session_cookie = response.cookies.get('passport_session')
                self.assertIsNotNone(session_cookie)
                self.assertTrue(session_cookie['httponly'])

    def test_valid_credentials_cannot_use_the_wrong_portal(self):
        cases = (
            ('portal-citizen@example.com', 'staff', 'citizen'),
            ('portal_test_officer', 'administrator', 'staff'),
            ('portal_test_admin', 'citizen', 'administrator'),
        )
        for identifier, portal_role, correct_portal in cases:
            with self.subTest(portal_role=portal_role):
                response = self.client.post(
                    '/api/login/',
                    {
                        'email': identifier,
                        'password': self.password,
                        'portal_role': portal_role,
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data['code'], 'wrong_portal')
                self.assertEqual(response.data['correct_portal'], correct_portal)
        self.assertEqual(AuthToken.objects.count(), 0)

    def test_invalid_portal_is_rejected(self):
        response = self.client.post(
            '/api/login/',
            {
                'email': 'portal-citizen@example.com',
                'password': self.password,
                'portal_role': 'unknown',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'invalid_portal')
        self.assertEqual(AuthToken.objects.count(), 0)

    def test_legacy_api_login_without_portal_role_still_works(self):
        response = self.client.post(
            '/api/login/',
            {'email': 'portal-citizen@example.com', 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'citizen')


class PublicInformationPageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_simplified_public_pages_render(self):
        cases = (
            ('/', 'Three stages from application to passport'),
            ('/how-to-apply/', 'How to apply for a passport'),
            ('/requirements/', 'Requirements and passport fees'),
            ('/privacy/', 'Privacy notice'),
            ('/terms/', 'Terms of use'),
            ('/security/', 'Security guidelines'),
        )
        for url, expected_text in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)


class RegistrationValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def valid_payload(self, **overrides):
        payload = {
            'role': 'citizen',
            'first_name': 'Registration',
            'middle_name': 'Test',
            'last_name': 'Citizen',
            'email': 'registration-citizen@example.com',
            'phone': '9841234567',
            'password': 'StrongPass!8472',
            'confirm_password': 'StrongPass!8472',
            'date_of_birth': '1997-05-14',
            'gender': 'Other',
            'nationality': 'Nepali',
            'address': 'Lalitpur, Nepal',
            'accepted_terms': True,
        }
        payload.update(overrides)
        return payload

    def test_required_fields_are_returned_as_field_errors(self):
        response = self.client.post('/api/register/', {'role': 'citizen'}, format='json')
        self.assertEqual(response.status_code, 400)
        for field in (
            'first_name', 'last_name', 'email', 'phone', 'password', 'confirm_password',
            'date_of_birth', 'gender', 'nationality', 'address',
            'accepted_terms',
        ):
            self.assertIn(field, response.data)
        self.assertNotIn('error', response.data)

    def test_invalid_email_phone_dob_and_password_return_correct_fields(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = self.client.post(
            '/api/register/',
            self.valid_payload(
                email='not-an-email',
                phone='12345',
                date_of_birth=tomorrow.isoformat(),
                password='12345678',
                confirm_password='12345678',
            ),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
        self.assertIn('phone', response.data)
        self.assertIn('date_of_birth', response.data)
        self.assertIn('password', response.data)

    def test_duplicate_email_and_phone_return_separate_field_errors(self):
        Applicant.objects.create(
            full_name='Existing Citizen',
            email='existing@example.com',
            phone='9861234567',
            password='StrongPass!8472',
            date_of_birth='1990-01-01',
            gender='Male',
            nationality='Nepali',
            address='Bhaktapur',
        )
        response = self.client.post(
            '/api/register/',
            self.valid_payload(email='EXISTING@example.com', phone='9861234567'),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
        self.assertIn('phone', response.data)

    def test_confirm_password_mismatch_is_attached_to_confirmation_field(self):
        response = self.client.post(
            '/api/register/',
            self.valid_payload(confirm_password='DifferentPass!8472'),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('confirm_password', response.data)

    def test_password_similarity_rule_is_attached_to_password_field(self):
        response = self.client.post(
            '/api/register/',
            self.valid_payload(
                email='similarity@example.com',
                password='similarity@example.com',
                confirm_password='similarity@example.com',
            ),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_valid_registration_creates_account_and_allows_login(self):
        response = self.client.post(
            '/api/register/',
            self.valid_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        applicant = Applicant.objects.get(email='registration-citizen@example.com')
        self.assertEqual(applicant.phone, '9841234567')
        login = self.client.post(
            '/api/login/',
            {
                'email': applicant.email,
                'password': 'StrongPass!8472',
                'portal_role': 'citizen',
            },
            format='json',
        )
        self.assertEqual(login.status_code, 200)

    def test_legacy_unverified_account_is_not_blocked(self):
        applicant = Applicant.objects.create(
            full_name='Unverified Citizen',
            email='unverified@example.com',
            phone='9841234598',
            password='StrongPass!8472',
            date_of_birth='1997-05-14',
            gender='Other',
            nationality='Nepali',
            address='Lalitpur',
            email_verified_at=None,
        )
        response = self.client.post(
            '/api/login/',
            {'email': applicant.email, 'password': 'StrongPass!8472', 'portal_role': 'citizen'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        raw_token, _ = AuthToken.issue('applicant', applicant.applicant_id)
        authenticated_client = APIClient()
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_token}')
        protected = authenticated_client.get(f'/api/applicants/{applicant.applicant_id}/')
        self.assertEqual(protected.status_code, 200)

    def test_removed_email_verification_endpoints_return_not_found(self):
        verify_response = self.client.post(
            '/api/registration/email-verification/verify/',
            {'token': 'unused'},
            format='json',
        )
        resend_response = self.client.post(
            '/api/registration/email-verification/resend/',
            {'email': 'registration-citizen@example.com'},
            format='json',
        )
        self.assertEqual(verify_response.status_code, 404)
        self.assertEqual(resend_response.status_code, 404)

class SecureBrowserSessionTests(TestCase):
    def setUp(self):
        self.password = 'SecureSession!8472'
        self.applicant = Applicant.objects.create(
            full_name='Cookie Session Citizen',
            email='cookie-session@example.com',
            phone='9840000021',
            password=self.password,
            date_of_birth='1994-04-04',
            gender='Other',
            nationality='Nepali',
            address='Kathmandu',
        )

    def test_cookie_authentication_requires_csrf_for_unsafe_requests(self):
        client = APIClient(enforce_csrf_checks=True)
        page = client.get('/login/')
        csrf_token = page.cookies['csrftoken'].value
        login = client.post(
            '/api/login/',
            {'email': self.applicant.email, 'password': self.password},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login.status_code, 200)
        self.assertNotIn('token', login.data)
        self.assertTrue(login.cookies['passport_session']['httponly'])

        authenticated_get = client.get('/api/applications/current-workflow/')
        self.assertEqual(authenticated_get.status_code, 200)

        rejected_logout = client.post('/api/logout/', {}, format='json')
        self.assertEqual(rejected_logout.status_code, 403)
        accepted_logout = client.post(
            '/api/logout/', {}, format='json', HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted_logout.status_code, 200)
        self.assertEqual(accepted_logout.cookies['passport_session']['max-age'], 0)

    def test_pages_receive_nonce_based_content_security_policy(self):
        response = self.client.get('/')
        policy = response.headers['Content-Security-Policy']
        nonce_match = re.search(r"script-src 'self' 'nonce-([^']+)'", policy)
        self.assertIsNotNone(nonce_match)
        self.assertContains(response, f'nonce="{nonce_match.group(1)}"')
        self.assertIn("object-src 'none'", policy)

    @override_settings(ESEWA_PAYMENT_URL='https://checkout.example.test/payments/start')
    def test_content_security_policy_allows_configured_esewa_form_origin(self):
        response = self.client.get('/applicant/apply/')
        policy = response.headers['Content-Security-Policy']
        self.assertIn(
            "form-action 'self' https://checkout.example.test",
            policy,
        )
        self.assertNotIn('/payments/start', policy)


@override_settings(
    PERSONNEL_MFA_REQUIRED=True,
    MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}},
)
class PersonnelMfaTests(TestCase):
    def setUp(self):
        self.password = 'PersonnelMfa!8472'
        self.staff = Staff.objects.create(
            full_name='MFA Test Officer',
            username='mfa_test_officer',
            email='mfa-officer@example.com',
            phone='9840000022',
            password=self.password,
        )

    def test_staff_must_complete_emailed_code_before_session_is_issued(self):
        client = APIClient()
        first_step = client.post(
            '/api/login/',
            {'username': self.staff.username, 'password': self.password, 'portal_role': 'staff'},
            format='json',
        )
        self.assertEqual(first_step.status_code, 202)
        self.assertTrue(first_step.data['mfa_required'])
        self.assertNotIn('passport_session', first_step.cookies)
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)

        completed = client.post(
            '/api/login/mfa/verify/',
            {'challenge_id': first_step.data['challenge_id'], 'code': code},
            format='json',
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data['role'], 'staff')
        self.assertNotIn('token', completed.data)
        self.assertTrue(completed.cookies['passport_session']['httponly'])

        replay = client.post(
            '/api/login/mfa/verify/',
            {'challenge_id': first_step.data['challenge_id'], 'code': code},
            format='json',
        )
        self.assertEqual(replay.status_code, 400)


class WorkflowRegressionTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Completed Workflow Citizen',
            email='workflow-complete@example.com',
            phone='9840000023',
            password='WorkflowPass!8472',
            date_of_birth='1992-02-02',
            gender='Other',
            nationality='Nepali',
            address='Pokhara',
        )
        self.application = Application.objects.create(
            applicant=self.applicant,
            biometric_status='Verified',
            passport_number='NP0000001',
        )
        for document_type, filename, content_type, content in (
            ('Citizenship Certificate', 'identity.pdf', 'application/pdf', b'%PDF-1.4\n%%EOF'),
            ('Passport Photo', 'photo.jpg', 'image/jpeg', b'photo'),
        ):
            Document.objects.create(
                application=self.application,
                document_type=document_type,
                file_name=filename,
                file_path=SimpleUploadedFile(filename, content, content_type=content_type),
                verification_status='Verified',
                is_inspected=True,
            )
        Payment.objects.create(
            application=self.application,
            applicant=self.applicant,
            payment_reference='WORKFLOW-COMPLETE-PAYMENT',
            transaction_id='WORKFLOW-COMPLETE-TXN',
            amount=self.application.fee_amount,
            status='VERIFIED',
            payment_status='Completed',
        )
        DigitalSignature.objects.create(
            application=self.application,
            signature_hash='test-signature',
            payload_hash='test-payload',
            is_valid=True,
        )
        QueueToken.objects.create(
            application=self.application,
            token_number=101,
            queue_status='Completed',
        )
        self.application.status = 'Approved'
        self.application.save()

    def test_completed_current_workflow_does_not_crash_and_allows_download(self):
        client = APIClient()
        client.force_authenticate(user=CustomUser(self.applicant, 'applicant'))
        response = client.get('/api/applications/current-workflow/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['can_download_pdf'])
        self.assertEqual(response.data['current_step'], 'passport_ready')
        self.assertEqual(response.data['queue_token']['queue_status'], 'Completed')
        self.assertTrue(response.data['steps'][-1]['can_download'])


class PassportNumberSequenceTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Sequential Passport Citizen',
            email='passport-sequence@example.com',
            phone='9840000030',
            password='SequencePass!8472',
            date_of_birth='1990-01-01',
            gender='Other',
            nationality='Nepali',
            address='Kathmandu',
        )
        self.first_application = Application.objects.create(applicant=self.applicant)
        self.second_application = Application.objects.create(applicant=self.applicant)

    def test_passport_numbers_are_sequential_and_idempotent(self):
        first = assign_passport_number(self.first_application)
        repeated = assign_passport_number(self.first_application)
        second = assign_passport_number(self.second_application)

        self.assertEqual(first, 'NP0000001')
        self.assertEqual(repeated, first)
        self.assertEqual(second, 'NP0000002')

        line_one, line_two = build_td3_mrz(self.first_application)
        self.assertEqual(len(line_one), 44)
        self.assertEqual(len(line_two), 44)
        self.assertTrue(line_two.startswith('NP0000001'))

    def test_rolled_back_allocation_does_not_create_a_gap(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                assign_passport_number(self.first_application)
                raise RuntimeError('Simulated queue completion failure')

        self.first_application.refresh_from_db()
        self.assertIsNone(self.first_application.passport_number)
        self.assertEqual(
            assign_passport_number(self.second_application),
            'NP0000001',
        )


class PublicTrackingPrivacyTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Private Tracking Citizen',
            email='private-tracking@example.com',
            phone='9840000024',
            password='TrackingPass!8472',
            date_of_birth='1991-03-05',
            gender='Other',
            nationality='Nepali',
            address='Dharan',
        )
        self.application = Application.objects.create(applicant=self.applicant)

    def test_opaque_reference_and_birth_date_are_both_required(self):
        client = APIClient()
        sequential = client.get('/api/track/', {'query': self.application.application_id, 'date_of_birth': '1991-03-05'})
        self.assertEqual(sequential.status_code, 400)
        wrong_birth_date = client.get('/api/track/', {'reference': self.application.tracking_reference, 'date_of_birth': '1990-01-01'})
        self.assertEqual(wrong_birth_date.status_code, 404)
        success = client.get('/api/track/', {'reference': self.application.tracking_reference, 'date_of_birth': '1991-03-05'})
        self.assertEqual(success.status_code, 200)
        self.assertNotIn('tracking_reference', success.data)
        self.assertNotIn(self.applicant.email, str(success.data))
        self.assertTrue(success.data['applicant_name'].startswith('P'))


class AuthorizationMatrixTests(TestCase):
    def setUp(self):
        self.first = Applicant.objects.create(
            full_name='First Citizen', email='first-authz@example.com', phone='9840000025',
            password='AuthzPass!8472', date_of_birth='1990-01-01', gender='Other',
            nationality='Nepali', address='Kathmandu',
        )
        self.second = Applicant.objects.create(
            full_name='Second Citizen', email='second-authz@example.com', phone='9840000026',
            password='AuthzPass!8472', date_of_birth='1990-01-01', gender='Other',
            nationality='Nepali', address='Kathmandu',
        )
        self.first_app = Application.objects.create(applicant=self.first)
        self.second_app = Application.objects.create(applicant=self.second)
        self.staff = Staff.objects.create(
            full_name='Authorization Officer', username='authz_officer',
            email='authz-officer@example.com', phone='9840000027', password='AuthzPass!8472',
        )

    def test_citizen_is_scoped_to_own_application_but_staff_can_review_both(self):
        client = APIClient()
        client.force_authenticate(user=CustomUser(self.first, 'applicant'))
        self.assertEqual(client.get(f'/api/applications/{self.first_app.pk}/').status_code, 200)
        self.assertEqual(client.get(f'/api/applications/{self.second_app.pk}/').status_code, 404)

        client.force_authenticate(user=CustomUser(self.staff, 'staff'))
        self.assertEqual(client.get(f'/api/applications/{self.first_app.pk}/').status_code, 200)
        self.assertEqual(client.get(f'/api/applications/{self.second_app.pk}/').status_code, 200)


class PaymentWebhookSecurityTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Payment Webhook Citizen', email='webhook@example.com', phone='9840000028',
            password='WebhookPass!8472', date_of_birth='1990-01-01', gender='Other',
            nationality='Nepali', address='Kathmandu',
        )
        self.application = Application.objects.create(applicant=self.applicant)
        self.payment = Payment.objects.create(
            application=self.application, applicant=self.applicant,
            payment_reference='SIGNED-WEBHOOK-REF', amount='5000.00', status='QR_GENERATED',
            payment_status='Pending', gateway_name='eSewa',
        )

    def test_signed_retry_is_idempotent_and_forged_retry_is_rejected(self):
        payload = {
            'payment_reference': self.payment.payment_reference,
            'amount': '5000.00',
            'transaction_id': 'ESEWA-TXN-IDEMPOTENT-1',
            'status': 'COMPLETE',
        }
        signature = PaymentService.generate_signature(
            f"{payload['payment_reference']}|{payload['amount']}|{payload['transaction_id']}"
        )
        client = APIClient()
        first = client.post('/api/payments/webhook/', payload, format='json', HTTP_X_GATEWAY_SIGNATURE=signature)
        self.assertEqual(first.status_code, 200)
        audit_count = ActivityLog.objects.count()
        notification_count = Notification.objects.count()

        repeated = client.post('/api/payments/webhook/', payload, format='json', HTTP_X_GATEWAY_SIGNATURE=signature)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(ActivityLog.objects.count(), audit_count)
        self.assertEqual(Notification.objects.count(), notification_count)

        forged = client.post('/api/payments/webhook/', payload, format='json', HTTP_X_GATEWAY_SIGNATURE='forged')
        self.assertEqual(forged.status_code, 400)


class SignatureAndUploadSecurityTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            full_name='Signature Citizen', email='signature@example.com', phone='9840000029',
            password='SignaturePass!8472', date_of_birth='1990-01-01', gender='Other',
            nationality='Nepali', address='Kathmandu',
        )
        self.application = Application.objects.create(applicant=self.applicant)
        Payment.objects.create(
            application=self.application, applicant=self.applicant,
            payment_reference='SIGNATURE-PAYMENT', transaction_id='SIGNATURE-TXN',
            amount='5000.00', status='VERIFIED', payment_status='Completed',
        )

    def test_signature_verification_detects_application_tampering(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode('utf-8')
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')
        with override_settings(
            PASSPORT_SIGNING_PRIVATE_KEY=private_pem,
            PASSPORT_SIGNING_PUBLIC_KEY=public_pem,
        ):
            signed = sign_application(self.application)
            signature = DigitalSignature.objects.create(
                application=self.application,
                signature_hash=signed['signature'],
                payload_hash=signed['payload_hash'],
                algorithm=signed['algorithm'],
                key_id=signed['key_id'],
                is_valid=True,
            )
            self.assertTrue(verify_signature(signature))
            self.application.passport_category = 'Ordinary (66 Pages)'
            self.application.save(update_fields=['passport_category'])
            self.assertFalse(verify_signature(signature))

    def test_final_signature_protects_sequential_passport_number(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode('utf-8')
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')
        self.application.passport_number = 'NP0000001'
        self.application.save(update_fields=['passport_number'])

        with override_settings(
            PASSPORT_SIGNING_PRIVATE_KEY=private_pem,
            PASSPORT_SIGNING_PUBLIC_KEY=public_pem,
        ):
            signed = sign_application(self.application)
            signature = DigitalSignature.objects.create(
                application=self.application,
                signature_hash=signed['signature'],
                payload_hash=signed['payload_hash'],
                credential_schema=signed['credential_schema'],
                algorithm=signed['algorithm'],
                key_id=signed['key_id'],
                is_valid=True,
            )
            self.assertEqual(signature.credential_schema, 'np-passport-credential-v2')
            self.assertTrue(verify_signature(signature))

            self.application.passport_number = 'NP0000002'
            self.application.save(update_fields=['passport_number'])
            self.assertFalse(verify_signature(signature))

    def test_active_pdf_content_and_fake_images_are_rejected(self):
        active_pdf = SimpleUploadedFile(
            'unsafe.pdf', b'%PDF-1.4\n/OpenAction 1 0 R\n%%EOF', content_type='application/pdf',
        )
        fake_image = SimpleUploadedFile(
            'fake.jpg', b'<html>not an image</html>', content_type='image/jpeg',
        )
        with self.assertRaises(UploadSecurityError):
            validate_uploaded_document(active_pdf, 'Citizenship Certificate')
        with self.assertRaises(UploadSecurityError):
            validate_uploaded_document(fake_image, 'Passport Photo')
