from django.db import models
from django.contrib.auth.hashers import make_password


# 1. APPLICANT

class Applicant(models.Model):
    applicant_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    nationality = models.CharField(max_length=50, default="Nepali")
    address = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name



# 2. STAFF


class Staff(models.Model):
    staff_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    status = models.CharField(max_length=20, default="Active")

    def save(self, *args, **kwargs):
        if not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name



# 3. ADMINISTRATOR


class Administrator(models.Model):
    admin_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)

    def save(self, *args, **kwargs):
        if not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


# 4. APPLICATION


class Application(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Under Review", "Under Review"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Completed", "Completed"),
    ]

    application_id = models.AutoField(primary_key=True)

    # APPLICANT 1 : N APPLICATION
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    # STAFF 1 : N APPLICATION
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_applications"
    )

    submission_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Application #{self.application_id}"

# 5. DOCUMENT

class Document(models.Model):

    VERIFICATION_CHOICES = [
        ("Pending", "Pending"),
        ("Verified", "Verified"),
        ("Rejected", "Rejected"),
    ]

    document_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : N DOCUMENT
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(max_length=100)

    file_name = models.CharField(max_length=255)

    file_path = models.FileField(
        upload_to="documents/"
    )

    upload_date = models.DateTimeField(auto_now_add=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default="Pending"
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.document_type

# 6. DIGITAL SIGNATURE


class DigitalSignature(models.Model):

    signature_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : 0..1 DIGITAL SIGNATURE
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="digital_signature"
    )

    signature_hash = models.CharField(
        max_length=255
    )

    signing_authority = models.CharField(
        max_length=200,
        default="Department of Passports, Government of Nepal"
    )

    certificate_serial = models.CharField(
        max_length=100,
        default="NPL-DOP-PKI-2026-001"
    )

    algorithm = models.CharField(
        max_length=50,
        default="RSA-SHA256"
    )

    signed_at = models.DateTimeField(
        auto_now_add=True
    )

    is_valid = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"Gov Digital Signature #{self.signature_id} - App #{self.application_id} ({self.signing_authority})"



# 7. QUEUE TOKEN

class QueueToken(models.Model):

    STATUS_CHOICES = [
        ("Waiting", "Waiting"),
        ("Called", "Called"),
        ("Serving", "Serving"),
        ("Completed", "Completed"),
        ("Skipped", "Skipped"),
    ]

    token_id = models.AutoField(primary_key=True)

    # APPLICATION 1 : 0..1 QUEUE TOKEN
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="queue_token"
    )

    # STAFF 1 : N QUEUE TOKEN
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queue_tokens"
    )

    token_number = models.PositiveIntegerField()

    token_date = models.DateField(
        auto_now_add=True
    )

    time_slot = models.TimeField(
        null=True,
        blank=True
    )

    queue_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Waiting"
    )

    called_time = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Token {self.token_number}"


# 8. REPORT

class Report(models.Model):

    report_id = models.AutoField(primary_key=True)

    # ADMINISTRATOR 1 : N REPORT
    administrator = models.ForeignKey(
        Administrator,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    report_type = models.CharField(
        max_length=100
    )

    report_date = models.DateTimeField(
        auto_now_add=True
    )

    report_data = models.JSONField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.report_type

# 9. ACTIVITY LOG

class ActivityLog(models.Model):

    log_id = models.AutoField(primary_key=True)

    # ADMINISTRATOR 1 : N ACTIVITY LOG
    administrator = models.ForeignKey(
        Administrator,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )

    action_taken = models.CharField(
        max_length=255
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.action_taken

# 10. NOTIFICATION

class Notification(models.Model):

    STATUS_CHOICES = [
        ("Unread", "Unread"),
        ("Read", "Read"),
    ]

    notification_id = models.AutoField(primary_key=True)

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    type = models.CharField(max_length=50)

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Unread"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.message[:50]

# 11. PAYMENT

class Payment(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    ]

    METHOD_CHOICES = [
        ("eSewa", "eSewa"),
        ("Khalti", "Khalti"),
        ("ConnectIPS", "ConnectIPS"),
        ("Bank Transfer", "Bank Transfer"),
        ("Digital Wallet", "Digital Wallet"),
    ]

    payment_id = models.AutoField(primary_key=True)

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="NPR"
    )

    payment_method = models.CharField(
        max_length=50,
        choices=METHOD_CHOICES,
        default="eSewa"
    )

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    remarks = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Payment #{self.payment_id} - App #{self.application_id} - {self.amount} {self.currency} ({self.payment_status})"


class AuthToken(models.Model):
    token_id = models.AutoField(primary_key=True)

    token = models.CharField(
        max_length=255,
        unique=True
    )

    user_type = models.CharField(
        max_length=20
    )

    user_id = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.token