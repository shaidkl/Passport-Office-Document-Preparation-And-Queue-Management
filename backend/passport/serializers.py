from rest_framework import serializers
from django.db.models import Q
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

# 1. APPLICANT

class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }


# 2. STAFF

class StaffSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone', required=False)

    class Meta:
        model = Staff
        fields = '__all__'
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False
            }
        }


# 3. ADMINISTRATOR

class AdministratorSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone', required=False)

    class Meta:
        model = Administrator
        fields = '__all__'
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False
            }
        }

# 4. APPLICATION

class ApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.full_name', read_only=True)
    applicant_email = serializers.CharField(source='applicant.email', read_only=True)
    applicant_phone = serializers.CharField(source='applicant.phone', read_only=True)
    fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    passport_type = serializers.CharField(read_only=True)
    passport_pages = serializers.CharField(read_only=True)
    delivery_type = serializers.CharField(read_only=True)
    queue_position = serializers.IntegerField(read_only=True)
    workflow_steps = serializers.SerializerMethodField(read_only=True)
    can_download_pdf = serializers.SerializerMethodField(read_only=True)
    passport_status = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Application

        fields = '__all__'

        read_only_fields = [
            'application_id',
            'submission_date',
            'last_updated',
        ]
        extra_kwargs = {
            'applicant': {'required': False}
        }

    def get_workflow_steps(self, obj):
        try:
            return obj.get_workflow_steps()
        except Exception:
            return []

    def get_can_download_pdf(self, obj):
        try:
            # Payment must be explicitly verified
            verified_payment = obj.payments.filter(
                Q(status='VERIFIED') | Q(payment_status='Completed')
            ).exists()
            if not verified_payment:
                return False

            # Required photo must exist and be verified
            has_photo = obj.documents.filter(document_type='Passport Photo', verification_status='Verified').exists()
            if not has_photo:
                return False

            return obj.status in ['Approved', 'Completed']
        except Exception:
            return False

# 5. DOCUMENT

class DocumentSerializer(serializers.ModelSerializer):
    application_ref = serializers.SerializerMethodField(read_only=True)
    applicant_name = serializers.CharField(source='application.applicant.full_name', read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = '__all__'

        read_only_fields = [
            'document_id',
            'upload_date',
        ]

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None

    def get_file_url(self, obj):
        if obj.file_path:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.file_path.url)
                return obj.file_path.url
            except Exception:
                return None
        return None

# 6. DIGITAL SIGNATURE

class DigitalSignatureSerializer(serializers.ModelSerializer):
    application_ref = serializers.SerializerMethodField(read_only=True)
    applicant_name = serializers.CharField(source='application.applicant.full_name', read_only=True)

    class Meta:
        model = DigitalSignature
        fields = '__all__'

        read_only_fields = [
            'signature_id',
            'signed_at',
        ]

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None

# 7. QUEUE TOKEN

class QueueTokenSerializer(serializers.ModelSerializer):
    application_ref = serializers.SerializerMethodField(read_only=True)
    applicant_name = serializers.CharField(source='application.applicant.full_name', read_only=True)
    applicant_phone = serializers.CharField(source='application.applicant.phone', read_only=True)
    passport_category = serializers.CharField(source='application.passport_category', read_only=True)
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)

    class Meta:
        model = QueueToken
        fields = '__all__'

        read_only_fields = [
            'token_id',
            'token_date',
        ]

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None

# 8. REPORT

class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = '__all__'

        read_only_fields = [
            'report_id',
            'generated_date',
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

# 11. PAYMENT
class PaymentSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.full_name', read_only=True)
    application_ref = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'

        read_only_fields = [
            'payment_id',
            'payment_date',
            'created_at',
            'updated_at',
            'paid_at',
            'verified_at',
        ]

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None