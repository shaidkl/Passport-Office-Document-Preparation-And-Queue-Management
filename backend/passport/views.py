from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
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
    Notification
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
    permission_classes = [IsStaffOrAdministrator]


class DigitalSignatureViewSet(viewsets.ModelViewSet):
    queryset = DigitalSignature.objects.all()
    serializer_class = DigitalSignatureSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsStaffOrAdministrator]


class QueueTokenViewSet(viewsets.ModelViewSet):
    queryset = QueueToken.objects.all()
    serializer_class = QueueTokenSerializer
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsStaffOrAdministrator]


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

            if administrator.status != "Active":
                return Response(
                    {
                        "error": "Administrator account is inactive."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

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

    return Response(
        {
            "error": "Invalid email or password."
        },
        status=status.HTTP_401_UNAUTHORIZED
    )