from django.shortcuts import render
from django.conf import settings

# --- PUBLIC VIEWS ---
def landing_page(request):
    return render(request, 'public/landing.html')

def login_page(request):
    return render(request, 'public/login.html')

def register_page(request):
    return render(request, 'public/register.html')

def track_page(request):
    return render(request, 'public/track.html')

# --- APPLICANT VIEWS ---
def applicant_dashboard(request):
    return render(request, 'applicant/dashboard.html')

def applicant_apply(request):
    return render(request, 'applicant/apply.html')

def applicant_documents(request):
    return render(request, 'applicant/documents.html')

def applicant_queue(request):
    return render(request, 'applicant/queue.html')

def applicant_notifications(request):
    return render(request, 'applicant/notifications.html')

def applicant_profile(request):
    return render(request, 'applicant/profile.html')

# --- STAFF VIEWS ---
def staff_dashboard(request):
    return render(request, 'staff/dashboard.html')

def staff_queue(request):
    return render(request, 'staff/queue.html')

def staff_verify(request):
    return render(request, 'staff/verify.html')

# --- ADMIN VIEWS ---
def admin_dashboard(request):
    return render(request, 'admin/dashboard.html')

def admin_applications(request):
    return render(request, 'admin/applications.html')

def admin_staff(request):
    return render(request, 'admin/staff.html')

def admin_reports(request):
    return render(request, 'admin/reports.html')

def admin_activity_logs(request):
    return render(request, 'admin/activity_logs.html')
