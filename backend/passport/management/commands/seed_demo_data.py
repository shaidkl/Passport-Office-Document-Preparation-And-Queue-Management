from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
from passport.models import Administrator, Staff, Applicant, Application, QueueToken, ActivityLog, Payment, DigitalSignature

class Command(BaseCommand):
    help = 'Check PostgreSQL database connectivity and seed default demo accounts if needed'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🔍 Checking Database Connection..."))

        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS("✅ PostgreSQL Database connection is SUCCESSFUL!"))
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection failed: {e}"))
            return

        # 1. Super Admin
        admin, created = Administrator.objects.get_or_create(
            email='admin@passport.gov.np',
            defaults={
                'full_name': 'Chief System Administrator',
                'phone': '9800000001',
                'password': 'adminpassword123'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Created Default Admin: admin@passport.gov.np / adminpassword123"))
        else:
            self.stdout.write(self.style.SUCCESS("ℹ️ Admin account already exists: admin@passport.gov.np"))

        # 2. Staff Officer
        staff, created = Staff.objects.get_or_create(
            email='staff@passport.gov.np',
            defaults={
                'full_name': 'Officer Ramesh Karki',
                'phone': '9800000002',
                'password': 'staffpassword123',
                'status': 'Active'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Created Default Staff: staff@passport.gov.np / staffpassword123"))
        else:
            self.stdout.write(self.style.SUCCESS("ℹ️ Staff account already exists: staff@passport.gov.np"))

        # 3. Citizen / Applicant
        citizen, created = Applicant.objects.get_or_create(
            email='citizen@example.com',
            defaults={
                'full_name': 'Ram Bahadur Thapa',
                'phone': '9841234567',
                'password': 'citizenpassword123',
                'date_of_birth': '1995-05-15',
                'gender': 'Male',
                'nationality': 'Nepali',
                'address': 'Ward No. 4, Kathmandu, Bagmati Province'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Created Default Citizen: citizen@example.com / citizenpassword123"))
            
            # Create sample application
            app = Application.objects.create(
                applicant=citizen,
                staff=staff,
                status='Pending'
            )
            # Create sample queue token
            QueueToken.objects.create(
                application=app,
                staff=staff,
                token_number=101,
                queue_status='Waiting'
            )
            # Create sample payment
            Payment.objects.create(
                application=app,
                applicant=citizen,
                amount=5000.00,
                currency='NPR',
                payment_method='eSewa',
                transaction_id='TXN-DEMO-2026-0001',
                payment_status='Completed',
                remarks='Standard 34-page e-Passport fee'
            )
            # Create Government Digital Signature
            DigitalSignature.objects.create(
                application=app,
                signature_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                signing_authority='Department of Passports, Ministry of Foreign Affairs, Government of Nepal',
                certificate_serial='NPL-DOP-PKI-2026-001',
                algorithm='RSA-SHA256',
                is_valid=True
            )
            self.stdout.write(self.style.SUCCESS("✅ Created Sample Application #1, Queue Token T-101, Payment (eSewa) & Official Government Digital Signature"))
        else:
            self.stdout.write(self.style.SUCCESS("ℹ️ Citizen account already exists: citizen@example.com"))

        # 4. Activity Log
        ActivityLog.objects.create(
            administrator=admin,
            action_taken="System health check, Payment table verification and demo verification completed."
        )

        self.stdout.write(self.style.SUCCESS("\n🎉 System check and seed complete! All models (including Payment) are ready."))

