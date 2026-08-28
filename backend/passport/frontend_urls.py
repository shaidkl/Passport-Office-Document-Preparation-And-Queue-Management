from django.urls import path
from . import frontend_views as views

urlpatterns = [
    # Public
    path('', views.landing_page, name='landing'),
    path('login/', views.login_page, name='login-page'),
    path('register/', views.register_page, name='register-page'),
    path('track/', views.track_page, name='track-page'),

    # Applicant Portal
    path('applicant/dashboard/', views.applicant_dashboard, name='applicant-dashboard'),
    path('applicant/apply/', views.applicant_apply, name='applicant-apply'),
    path('applicant/documents/', views.applicant_documents, name='applicant-documents'),
    path('applicant/queue/', views.applicant_queue, name='applicant-queue'),
    path('applicant/notifications/', views.applicant_notifications, name='applicant-notifications'),
    path('applicant/profile/', views.applicant_profile, name='applicant-profile'),

    # Staff Portal
    path('staff/dashboard/', views.staff_dashboard, name='staff-dashboard'),
    path('staff/queue/', views.staff_queue, name='staff-queue'),
    path('staff/verify/', views.staff_verify, name='staff-verify'),

    # Admin Portal
    path('admin-portal/dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin-portal/applications/', views.admin_applications, name='admin-applications'),
    path('admin-portal/staff/', views.admin_staff, name='admin-staff'),
    path('admin-portal/reports/', views.admin_reports, name='admin-reports'),
    path('admin-portal/activity-logs/', views.admin_activity_logs, name='admin-activity-logs'),
]
