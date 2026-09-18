from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
import re
import unicodedata
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
from .workflow_service import build_workflow_facts


def _login_identifier_exists(value, instance=None):
    """Keep email/username identifiers unambiguous across every portal."""
    normalized = str(value or '').strip()
    if not normalized:
        return False

    applicant_query = Applicant.objects.filter(email__iexact=normalized)
    staff_query = Staff.objects.filter(
        Q(email__iexact=normalized) | Q(username__iexact=normalized)
    )
    administrator_query = Administrator.objects.filter(
        Q(email__iexact=normalized) | Q(username__iexact=normalized)
    )

    if isinstance(instance, Applicant):
        applicant_query = applicant_query.exclude(pk=instance.pk)
    elif isinstance(instance, Staff):
        staff_query = staff_query.exclude(pk=instance.pk)
    elif isinstance(instance, Administrator):
        administrator_query = administrator_query.exclude(pk=instance.pk)

    return (
        applicant_query.exists()
        or staff_query.exists()
        or administrator_query.exists()
    )


def _normalize_nepal_mobile(value):
    phone = re.sub(r'[\s\-+()]', '', str(value or ''))
    if phone.startswith('977'):
        phone = phone[3:]
    if not re.fullmatch(r'9[678]\d{8}', phone):
        raise serializers.ValidationError('Enter a valid 10-digit Nepali mobile number.')
    return phone


class CitizenRegistrationSerializer(serializers.Serializer):
    """Authoritative validation for public citizen registration."""

    role = serializers.ChoiceField(choices=['citizen'], default='citizen')
    first_name = serializers.CharField(max_length=50)
    middle_name = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        trim_whitespace=False,
    )
    confirm_password = serializers.CharField(
        max_length=128,
        write_only=True,
        trim_whitespace=False,
    )
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=['Male', 'Female', 'Other'])
    nationality = serializers.CharField(max_length=50)
    address = serializers.CharField(max_length=255)
    accepted_terms = serializers.BooleanField()

    @staticmethod
    def _validate_name_part(value, label, required=True):
        value = ' '.join(str(value or '').strip().split())
        if not value:
            if required:
                raise serializers.ValidationError(f'Enter your {label}.')
            return ''

        allowed_separators = {"'", '-'}
        has_letter = False
        for character in value:
            category = unicodedata.category(character)
            if category.startswith('L'):
                has_letter = True
                continue
            if category.startswith('M') or character.isspace() or character in allowed_separators:
                continue
            raise serializers.ValidationError(
                f'{label.capitalize()} may contain letters, spaces, apostrophes, and hyphens only.'
            )
        if not has_letter:
            raise serializers.ValidationError(f'Enter a valid {label}.')
        return value

    def validate_first_name(self, value):
        return self._validate_name_part(value, 'first name')

    def validate_middle_name(self, value):
        return self._validate_name_part(value, 'middle name', required=False)

    def validate_last_name(self, value):
        return self._validate_name_part(value, 'last name')

    def validate_email(self, value):
        value = value.strip().lower()
        if _login_identifier_exists(value):
            raise serializers.ValidationError(
                'This email address is already registered. Please use another email or log in.'
            )
        return value

    def validate_phone(self, value):
        phone = re.sub(r'[\s\-+()]', '', str(value or ''))
        if phone.startswith('977'):
            phone = phone[3:]
        if not re.fullmatch(r'9[678]\d{8}', phone):
            raise serializers.ValidationError(
                'Enter a valid 10-digit Nepali mobile number (for example, 98XXXXXXXX).'
            )
        if Applicant.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                'This phone number is already registered. Please use another phone number or log in.'
            )
        return phone

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('Date of birth cannot be in the future.')
        return value

    def validate_password(self, value):
        registration_user = Applicant(
            email=str(self.initial_data.get('email') or '').strip(),
            full_name=' '.join(
                str(self.initial_data.get(field) or '').strip()
                for field in ('first_name', 'middle_name', 'last_name')
                if str(self.initial_data.get(field) or '').strip()
            ),
        )
        registration_user.first_name = str(self.initial_data.get('first_name') or '').strip()
        registration_user.last_name = str(self.initial_data.get('last_name') or '').strip()
        try:
            validate_password(value, user=registration_user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def validate_accepted_terms(self, value):
        if value is not True:
            raise serializers.ValidationError(
                'You must confirm that the registration details are accurate.'
            )
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return attrs

# 1. APPLICANT

class ApplicantSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        email = value.strip().lower()
        if _login_identifier_exists(email, self.instance):
            raise serializers.ValidationError('This sign-in email is already used by another account.')
        return email

    def validate_phone(self, value):
        phone = re.sub(r'[\s\-+()]', '', str(value or ''))
        if phone.startswith('977'):
            phone = phone[3:]
        if not re.fullmatch(r'9[678]\d{8}', phone):
            raise serializers.ValidationError('Enter a valid 10-digit Nepali mobile number.')
        duplicate = Applicant.objects.filter(phone=phone)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError('This phone number is already registered.')
        return phone

    def validate_password(self, value):
        try:
            validate_password(value, user=self.instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    class Meta:
        model = Applicant
        fields = '__all__'
        read_only_fields = ['email_verified_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }


# 2. STAFF

class StaffSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone', required=False)

    def validate_password(self, value):
        try:
            validate_password(value, user=self.instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def validate_phone_number(self, value):
        return _normalize_nepal_mobile(value)

    def validate_phone(self, value):
        return _normalize_nepal_mobile(value)

    def validate_email(self, value):
        email = value.strip().lower()
        if _login_identifier_exists(email, self.instance):
            raise serializers.ValidationError('This sign-in email is already used by another account.')
        return email

    def validate_username(self, value):
        username = str(value or '').strip()
        if username and _login_identifier_exists(username, self.instance):
            raise serializers.ValidationError('This sign-in username is already used by another account.')
        return username or None

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'A password is required for new staff accounts.'})
        email = attrs.get('email', getattr(self.instance, 'email', '') if self.instance else '')
        username = attrs.get('username', getattr(self.instance, 'username', '') if self.instance else '')
        if email and username and email.casefold() == username.casefold():
            raise serializers.ValidationError({'username': 'Username must be different from the email address.'})
        return super().validate(attrs)

    class Meta:
        model = Staff
        fields = '__all__'
        read_only_fields = ['is_active', 'status']
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False
            }
        }


# 3. ADMINISTRATOR

class AdministratorSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone', required=False)

    def validate_password(self, value):
        try:
            validate_password(value, user=self.instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def validate_phone_number(self, value):
        return _normalize_nepal_mobile(value)

    def validate_phone(self, value):
        return _normalize_nepal_mobile(value)

    def validate_email(self, value):
        email = value.strip().lower()
        if _login_identifier_exists(email, self.instance):
            raise serializers.ValidationError('This sign-in email is already used by another account.')
        return email

    def validate_username(self, value):
        username = str(value or '').strip()
        if username and _login_identifier_exists(username, self.instance):
            raise serializers.ValidationError('This sign-in username is already used by another account.')
        return username or None

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'A password is required for new administrator accounts.'})
        email = attrs.get('email', getattr(self.instance, 'email', '') if self.instance else '')
        username = attrs.get('username', getattr(self.instance, 'username', '') if self.instance else '')
        if email and username and email.casefold() == username.casefold():
            raise serializers.ValidationError({'username': 'Username must be different from the email address.'})
        return super().validate(attrs)

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
    ALLOWED_PASSPORT_CATEGORIES = {
        'Ordinary (34 Pages)',
        'Ordinary (66 Pages)',
        'Express Urgent',
    }
    ALLOWED_SERVICE_TYPES = {
        'New Passport',
        'Renewal',
        'Passport Renewal',
        'Replacement',
    }
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

    def validate_passport_category(self, value):
        if value not in self.ALLOWED_PASSPORT_CATEGORIES:
            raise serializers.ValidationError('Select a supported passport category.')
        return value

    def validate_service_type(self, value):
        if value not in self.ALLOWED_SERVICE_TYPES:
            raise serializers.ValidationError('Select a supported application reason.')
        return value

    def get_can_download_pdf(self, obj):
        try:
            return build_workflow_facts(obj)['can_download']
        except Exception:
            return False

# 5. DOCUMENT

class DocumentSerializer(serializers.ModelSerializer):
    application_ref = serializers.SerializerMethodField(read_only=True)
    application_status = serializers.CharField(source='application.status', read_only=True)
    applicant_name = serializers.CharField(source='application.applicant.full_name', read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    file_available = serializers.SerializerMethodField(read_only=True)
    is_replacement_upload = serializers.SerializerMethodField(read_only=True)

    DOCUMENT_TYPE_ALIASES = {
        'Citizenship Certificate': 'Citizenship Certificate',
        'National ID Card': 'National ID Card',
        'National ID (NID)': 'National ID Card',
        'Birth Certificate': 'Birth Certificate',
        'Passport Photo': 'Passport Photo',
        'Previous Passport': 'Previous Passport',
    }

    class Meta:
        model = Document
        exclude = ['file_content']

        read_only_fields = [
            'document_id',
            'upload_date',
        ]
        extra_kwargs = {
            'file_name': {'required': False},
            # Files are only served by the authenticated view-file endpoint.
            'file_path': {'write_only': True},
        }

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        raw_fp = data.get('file_path')
        if isinstance(raw_fp, str):
            raise serializers.ValidationError({
                'file_path': 'A real multipart file upload is required; filesystem paths are not accepted.'
            })
        if hasattr(raw_fp, 'name') and not data.get('file_name'):
            data['file_name'] = raw_fp.name
        return super().to_internal_value(data)

    def validate_document_type(self, value):
        normalized = str(value or '').strip()
        if normalized not in self.DOCUMENT_TYPE_ALIASES:
            raise serializers.ValidationError('Select a supported passport document type.')
        return self.DOCUMENT_TYPE_ALIASES[normalized]

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None

    def get_file_url(self, obj):
        if not obj.has_available_file():
            return None
        path = f'/api/documents/{obj.document_id}/view-file/'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def get_file_available(self, obj):
        return obj.has_available_file()

    def get_is_replacement_upload(self, obj):
        return bool(getattr(obj, '_is_replacement_upload', False))

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
    report_date = serializers.DateTimeField(source='generated_date', read_only=True)
    report_data = serializers.JSONField(source='data_payload', read_only=True)

    class Meta:
        model = Report
        fields = [
            'report_id',
            'administrator',
            'report_type',
            'report_date',
            'report_data',
        ]

        read_only_fields = [
            'report_id',
            'report_date',
            'administrator',
        ]

# 9. ACTIVITY LOG


class ActivityLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityLog
        fields = '__all__'

        read_only_fields = [
            'log_id',
            'timestamp',
            'administrator',
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
        extra_kwargs = {
            'applicant': {'required': False},
        }

    def validate(self, attrs):
        if not attrs.get('applicant') and attrs.get('application'):
            attrs['applicant'] = attrs['application'].applicant
        return super().validate(attrs)

    def get_application_ref(self, obj):
        if obj.application:
            return f"NP-{obj.application.application_id:04d}"
        return None
