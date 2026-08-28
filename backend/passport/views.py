from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError
import secrets
from .models import AuthToken
from rest_framework.permissions import IsAuthenticated
from .authentication import CustomTokenAuthentication

from .permissions import (
    IsAdministrator,
    IsStaff,
    IsApplicant,
    IsStaffOrAdministrator
)

from .models import (
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
)

from .serializers import (
    ApplicantSerializer,
    StaffSerializer,
    AdministratorSerializer,
    ApplicationSerializer,
    DocumentSerializer,
    DigitalSignatureSerializer,
    QueueTokenSerializer,
    ReportSerializer,
    ActivityLogSerializer,
    NotificationSerializer,
    PaymentSerializer,
)


# 1. APPLICANT API

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [
        IsApplicant | IsStaffOrAdministrator
    ]


# 2. STAFF API

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAdministrator]


class AdministratorViewSet(viewsets.ModelViewSet):
    queryset = Administrator.objects.all()
    serializer_class = AdministratorSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class DigitalSignatureViewSet(viewsets.ModelViewSet):
    queryset = DigitalSignature.objects.all()
    serializer_class = DigitalSignatureSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class QueueTokenViewSet(viewsets.ModelViewSet):
    queryset = QueueToken.objects.all()
    serializer_class = QueueTokenSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {
                "error": "Email and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check Administrator
    try:
        administrator = Administrator.objects.get(email=email)

        if check_password(password, administrator.password):

            token = secrets.token_hex(32)

            AuthToken.objects.create(
                token=token,
                user_type="administrator",
                user_id=administrator.admin_id
            )

            return Response({
                "message": "Login successful.",
                "role": "administrator",
                "user_id": administrator.admin_id,
                "name": administrator.full_name,
                "email": administrator.email,
                "token": token
            }, status=status.HTTP_200_OK)

    except Administrator.DoesNotExist:
        pass

    # Check Staff
    try:
        staff = Staff.objects.get(email=email)

        if check_password(password, staff.password):

            if staff.status != "Active":
                return Response(
                    {
                        "error": "Staff account is inactive."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            token = secrets.token_hex(32)

            AuthToken.objects.create(
                token=token,
                user_type="staff",
                user_id=staff.staff_id
            )

            return Response({
                "message": "Login successful.",
                "role": "staff",
                "user_id": staff.staff_id,
                "name": staff.full_name,
                "email": staff.email,
                "token": token
            }, status=status.HTTP_200_OK)

    except Staff.DoesNotExist:
        pass

    # Check Citizen
    try:
        applicant = Applicant.objects.get(email=email)

        if check_password(password, applicant.password):
            token = secrets.token_hex(32)

            AuthToken.objects.create(
                token=token,
                user_type="applicant",
                user_id=applicant.applicant_id
            )

            return Response({
                "message": "Login successful.",
                "role": "citizen",
                "user_id": applicant.applicant_id,
                "name": applicant.full_name,
                "email": applicant.email,
                "token": token
            }, status=status.HTTP_200_OK)

    except Applicant.DoesNotExist:
        pass

    return Response(
        {
            "error": "Invalid email or password."
        },
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
def register_view(request):
    role = request.data.get('role', 'citizen').lower()
    common_fields = ['full_name', 'email', 'phone', 'password']
    missing_fields = [field for field in common_fields if not request.data.get(field)]

    if role == 'citizen':
        required_fields = ['date_of_birth', 'gender', 'address']
    elif role in ('staff', 'administrator'):
        required_fields = []
    else:
        return Response({'error': 'Role must be citizen, staff, or administrator.'}, status=status.HTTP_400_BAD_REQUEST)

    missing_fields.extend(field for field in required_fields if not request.data.get(field))
    if missing_fields:
        return Response(
            {'error': f"Missing required fields: {', '.join(missing_fields)}."},
            status=status.HTTP_400_BAD_REQUEST
        )

    fields = {
        'full_name': request.data.get('full_name'),
        'email': request.data.get('email'),
        'phone': request.data.get('phone'),
        'password': request.data.get('password'),
    }

    if role == 'citizen':
        fields.update({
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),
            'nationality': request.data.get('nationality', 'Nepali'),
            'address': request.data.get('address'),
        })
        model = Applicant
    elif role == 'staff':
        model = Staff
    else:
        model = Administrator

    try:
        user = model.objects.create(**fields)
    except (IntegrityError, ValueError) as error:
        return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    user_id = user.applicant_id if role == 'citizen' else user.staff_id if role == 'staff' else user.admin_id

    return Response({
        'message': 'Registration successful. You can now log in.',
        'role': role,
        'user_id': user_id,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def track_application_view(request):
    """
    Public safe endpoint to track application status by application_id or token_number.
    Does not expose sensitive personal information.
    """
    query = request.query_params.get('query') or request.query_params.get('id')
    if not query:
        return Response(
            {"error": "Please provide an application ID or token number to track."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Clean query (remove 'NP-', '#', or whitespace)
    cleaned_query = query.upper().replace('NP-', '').replace('NP', '').replace('#', '').strip()

    application = None

    # 1. Try finding by application_id
    if cleaned_query.isdigit():
        application = Application.objects.filter(application_id=int(cleaned_query)).first()

    # 2. Try finding by QueueToken token_number
    if not application and cleaned_query.isdigit():
        token = QueueToken.objects.filter(token_number=int(cleaned_query)).first()
        if token:
            application = token.application

    if not application:
        return Response(
            {"error": f"No application found matching reference '{query}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Mask applicant name for privacy (e.g., "Ram Sharma" -> "R** S*****")
    def mask_name(name):
        if not name:
            return "Citizen"
        parts = name.split()
        masked = []
        for p in parts:
            if len(p) > 1:
                masked.append(p[0] + '*' * (len(p) - 1))
            else:
                masked.append(p)
        return ' '.join(masked)

    # Fetch Queue Token if exists
    token_data = None
    if hasattr(application, 'queue_token') and application.queue_token:
        token = application.queue_token
        token_data = {
            "token_number": token.token_number,
            "queue_status": token.queue_status,
            "token_date": str(token.token_date),
            "time_slot": str(token.time_slot) if token.time_slot else None,
            "called_time": str(token.called_time) if token.called_time else None,
        }

    # Document stats
    docs = application.documents.all()
    total_docs = docs.count()
    verified_docs = docs.filter(verification_status="Verified").count()

    response_data = {
        "application_id": application.application_id,
        "applicant_name": mask_name(application.applicant.full_name if application.applicant else None),
        "submission_date": application.submission_date,
        "status": application.status,
        "last_updated": application.last_updated,
        "documents_count": total_docs,
        "documents_verified": verified_docs,
        "queue_token": token_data,
    }

    return Response(response_data, status=status.HTTP_200_OK)