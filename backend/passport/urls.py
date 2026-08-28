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
    register_view,
    track_application_view
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
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('track/', track_application_view, name='track'),
]