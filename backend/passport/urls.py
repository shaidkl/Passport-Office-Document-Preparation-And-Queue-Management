from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicantViewSet,
    StaffViewSet,
    AdministratorViewSet,
    ApplicationViewSet,
    DocumentViewSet,
    DigitalSignatureViewSet,
    QueueTokenViewSet,
    ReportViewSet,
    ActivityLogViewSet,
    NotificationViewSet,
    PaymentViewSet,
    login_view,
    verify_login_mfa,
    logout_view,
    register_view,
    resend_registration_verification_email,
    verify_registration_email,
    track_application_view,
    verify_signature_view,
    staff_duty_status_view,
)


router = DefaultRouter()


# Applicant
router.register(
    r'applicants',
    ApplicantViewSet,
    basename='applicant'
)

# Staff
router.register(
    r'staff',
    StaffViewSet,
    basename='staff'
)

# Admin Staff Management alias
router.register(
    r'admin/staff',
    StaffViewSet,
    basename='admin-staff'
)

# Administrator
router.register(
    r'administrators',
    AdministratorViewSet,
    basename='administrator'
)

# Application
router.register(
    r'applications',
    ApplicationViewSet,
    basename='application'
)

# Document
router.register(
    r'documents',
    DocumentViewSet,
    basename='document'
)

# Digital Signature
router.register(
    r'digital-signatures',
    DigitalSignatureViewSet,
    basename='digital-signature'
)

# Queue Token
router.register(
    r'queue-tokens',
    QueueTokenViewSet,
    basename='queue-token'
)

# Payment
router.register(
    r'payments',
    PaymentViewSet,
    basename='payment'
)

# Report
router.register(
    r'reports',
    ReportViewSet,
    basename='report'
)

# Activity Log
router.register(
    r'activity-logs',
    ActivityLogViewSet,
    basename='activity-log'
)

# Notification
router.register(
    r'notifications',
    NotificationViewSet,
    basename='notification'
)


urlpatterns = [
    # Keep self-service duty status ahead of the staff CRUD router so it can
    # never be interpreted as an administrator-only staff detail route.
    path('staff/duty-status/', staff_duty_status_view, name='staff-duty-status-self'),
    path('', include(router.urls)),
    path('registration/email-verification/verify/', verify_registration_email, name='registration-email-verify'),
    path('registration/email-verification/resend/', resend_registration_verification_email, name='registration-email-resend'),
    path('login/', login_view, name='login'),
    path('login/mfa/verify/', verify_login_mfa, name='login-mfa-verify'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('track/', track_application_view, name='track'),
    path('signatures/verify/<uuid:verification_code>/', verify_signature_view, name='verify-signature'),
]
