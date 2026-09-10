from django.core.management.base import BaseCommand
from passport.models import Administrator

class Command(BaseCommand):
    help = 'Create or update a central Administrator account for the Passport Office system'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Admin username (e.g. admin or superadmin)')
        parser.add_argument('--email', type=str, default='admin@passport.gov.np', help='Admin official email')
        parser.add_argument('--password', type=str, default='adminpassword123', help='Admin account password')
        parser.add_argument('--name', type=str, default='Central System Administrator', help='Full name of administrator')
        parser.add_argument('--phone', type=str, default='9800000001', help='Contact phone number')

    def handle(self, *args, **options):
        username = options['username'].strip()
        email = options['email'].strip()
        password = options['password']
        name = options['name'].strip()
        phone = options['phone'].strip()

        admin = Administrator.objects.filter(email__iexact=email).first()
        if not admin and username:
            admin = Administrator.objects.filter(username__iexact=username).first()

        if admin:
            admin.full_name = name
            admin.username = username
            admin.email = email
            admin.phone = phone
            admin.password = password
            admin.is_active = True
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Administrator updated successfully: {username} ({email})"))
        else:
            admin = Administrator.objects.create(
                full_name=name,
                username=username,
                email=email,
                phone=phone,
                password=password,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Administrator created successfully: {username} ({email})"))
