from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0007_staff_admin_management_updates'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='passport_category',
            field=models.CharField(blank=True, default='Ordinary (34 Pages)', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='service_type',
            field=models.CharField(blank=True, default='New Passport', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='biometric_status',
            field=models.CharField(
                choices=[
                    ('Pending', 'Pending'),
                    ('Submitted', 'Submitted'),
                    ('Verified', 'Verified'),
                    ('Failed', 'Failed'),
                ],
                default='Pending',
                max_length=30,
            ),
        ),
    ]
