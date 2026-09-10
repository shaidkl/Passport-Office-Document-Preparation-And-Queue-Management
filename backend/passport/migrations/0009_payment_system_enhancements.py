from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0008_application_workflow_fields'),
    ]

    operations = [
        # ActivityLog enhancements
        migrations.AlterField(
            model_name='activitylog',
            name='administrator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='activity_logs',
                to='passport.administrator',
            ),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='application',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='activity_logs',
                to='passport.application',
            ),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),

        # Payment enhancements
        migrations.AddField(
            model_name='payment',
            name='payment_reference',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_type',
            field=models.CharField(
                choices=[
                    ('APPLICATION_FEE', 'Application Fee'),
                    ('URGENT_PROCESSING_FEE', 'Urgent Processing Fee'),
                    ('ADDITIONAL_SERVICE_FEE', 'Additional Service Fee'),
                ],
                default='APPLICATION_FEE',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'PENDING'),
                    ('QR_GENERATED', 'QR_GENERATED'),
                    ('PAYMENT_INITIATED', 'PAYMENT_INITIATED'),
                    ('PAID', 'PAID'),
                    ('VERIFIED', 'VERIFIED'),
                    ('FAILED', 'FAILED'),
                    ('EXPIRED', 'EXPIRED'),
                    ('CANCELLED', 'CANCELLED'),
                ],
                db_index=True,
                default='PENDING',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='gateway_name',
            field=models.CharField(blank=True, default='eSewa', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='qr_code',
            field=models.TextField(blank=True, help_text='SVG or Base64 Data URI of payment QR code', null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='qr_payload',
            field=models.TextField(blank=True, help_text='Standardized payload encoded in QR code', null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='failure_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
