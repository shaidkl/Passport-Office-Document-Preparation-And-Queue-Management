from rest_framework import serializers
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
)

# 1. APPLICANT

class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'


# 2. STAFF

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = '__all__'

        # Never return the password in GET responses
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }


# 3. ADMINISTRATOR

class AdministratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrator
        fields = '__all__'

        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

# 4. APPLICATION

class ApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Application
        fields = '__all__'

        read_only_fields = [
            'application_id',
            'submission_date',
            'last_updated',
        ]

# 5. DOCUMENT

class DocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = '__all__'

        read_only_fields = [
            'document_id',
            'upload_date',
        ]

# 6. DIGITAL SIGNATURE

class DigitalSignatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = DigitalSignature
        fields = '__all__'

        read_only_fields = [
            'signature_id',
        ]


# 7. QUEUE TOKEN

class QueueTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = QueueToken
        fields = '__all__'

        read_only_fields = [
            'token_id',
            'token_date',
        ]


# 8. REPORT

class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = '__all__'

        read_only_fields = [
            'report_id',
            'report_date',
        ]

# 9. ACTIVITY LOG

class ActivityLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityLog
        fields = '__all__'

        read_only_fields = [
            'log_id',
            'timestamp',
        ]

# 10. NOTIFICATION
class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = '__all__'

        read_only_fields = [
            'notification_id',
            'created_at',
        ]