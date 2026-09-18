from django.shortcuts import render
from django.conf import settings
from django.middleware.csrf import get_token


def _render(request, template_name, context=None):
    # Ensure browser pages receive a CSRF cookie before their JavaScript makes
    # an authenticated API request.
    get_token(request)
    return render(request, template_name, context)

# --- PUBLIC VIEWS ---
def landing_page(request):
    return _render(request, 'public/landing.html')

def login_page(request):
    return _render(request, 'public/login.html', {'portal_role': 'citizen'})

def staff_login_page(request):
    return _render(request, 'public/login.html', {'portal_role': 'staff'})

def admin_login_page(request):
    return _render(request, 'public/login.html', {'portal_role': 'administrator'})

def register_page(request):
    return _render(request, 'public/register.html')

def verify_email_page(request):
    return _render(request, 'public/verify_email.html')

def track_page(request):
    return _render(request, 'public/track.html')

def how_to_apply_page(request):
    return _render(request, 'public/how_to_apply.html')

def requirements_page(request):
    return _render(request, 'public/requirements.html')


LEGAL_PAGES = {
    'privacy': {
        'title_key': 'privacy_title', 'title': 'Privacy notice',
        'intro_key': 'privacy_intro',
        'intro': 'This academic demonstration processes test data to model a passport workflow. Do not submit real identity documents.',
        'sections': [
            ('privacy_data_title', 'Data handled', 'privacy_data_desc', 'Account details, uploaded files, application status, payment metadata, queue activity, and security logs may be stored.'),
            ('privacy_use_title', 'How data is used', 'privacy_use_desc', 'Data supports authentication, workflow processing, notifications, audit history, and project evaluation.'),
            ('privacy_protection_title', 'Protection', 'privacy_protection_desc', 'The project uses access controls, protected session cookies, CSRF checks, upload validation, and configurable encryption and scanning services.'),
            ('privacy_retention_title', 'Retention and deletion', 'privacy_retention_desc', 'Test data should be deleted after evaluation. A real deployment requires an approved retention schedule and a formal process for access or deletion requests.'),
        ],
    },
    'terms': {
        'title_key': 'terms_title', 'title': 'Terms of use',
        'intro_key': 'terms_intro',
        'intro': 'This site is an academic prototype, not a government service, and cannot issue a legally valid passport.',
        'sections': [
            ('terms_demo_title', 'Demonstration only', 'terms_demo_desc', 'Applications, payments, queue tokens, signatures, and generated documents are simulated unless an authorized operator explicitly configures approved services.'),
            ('terms_user_title', 'Acceptable use', 'terms_user_desc', 'Use test information, keep credentials private, and do not upload unlawful, malicious, or third-party personal material.'),
            ('terms_fees_title', 'Fees and payments', 'terms_fees_desc', 'Displayed fees and sandbox payment results are illustrative. Confirm current fees through an authorized government channel.'),
            ('terms_availability_title', 'Availability', 'terms_availability_desc', 'The prototype may change or be unavailable during development and is provided without a service-level guarantee.'),
        ],
    },
    'security': {
        'title_key': 'security_title', 'title': 'Security guidelines',
        'intro_key': 'security_intro',
        'intro': 'Use synthetic data in this demonstration and report security concerns to the project owner without exposing sensitive information.',
        'sections': [
            ('security_account_title', 'Protect accounts', 'security_account_desc', 'Use a unique password, never share verification codes, sign out on shared devices, and enable personnel MFA in every non-development environment.'),
            ('security_upload_title', 'Safe uploads', 'security_upload_desc', 'Upload only test files. Production requires an active malware scanner, private media storage, file-size limits, and strict type validation.'),
            ('security_deploy_title', 'Secure deployment', 'security_deploy_desc', 'Use HTTPS, strong secret keys, PostgreSQL credentials, secure cookies, trusted hosts, signed keys, backups, monitoring, and timely dependency updates.'),
            ('security_report_title', 'Report a concern', 'security_report_desc', 'Record the affected page, time, and safe reproduction steps. Do not include passwords, identity numbers, private keys, or uploaded documents.'),
        ],
    },
}


def legal_page(request, policy_slug):
    return _render(request, 'public/legal.html', {'policy': LEGAL_PAGES[policy_slug]})

# --- APPLICANT VIEWS ---
def applicant_dashboard(request):
    return _render(request, 'applicant/dashboard.html')

def applicant_apply(request):
    return _render(request, 'applicant/apply.html')

def applicant_documents(request):
    return _render(request, 'applicant/documents.html')

def applicant_queue(request):
    return _render(request, 'applicant/queue.html')

def applicant_notifications(request):
    return _render(request, 'applicant/notifications.html')

def applicant_profile(request):
    return _render(request, 'applicant/profile.html')

# --- STAFF VIEWS ---
def staff_dashboard(request):
    return _render(request, 'staff/dashboard.html')

def staff_queue(request):
    return _render(request, 'staff/queue.html')

def staff_verify(request):
    return _render(request, 'staff/verify.html')

# --- ADMIN VIEWS ---
def admin_dashboard(request):
    return _render(request, 'admin/dashboard.html')

def admin_applications(request):
    return _render(request, 'admin/applications.html')

def admin_staff(request):
    return _render(request, 'admin/staff.html')

def admin_reports(request):
    return _render(request, 'admin/reports.html')

def admin_activity_logs(request):
    return _render(request, 'admin/activity_logs.html')

def admin_payments(request):
    return _render(request, 'admin/payments.html')
