from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0004_applicant_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('payment_id', models.AutoField(primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='NPR', max_length=10)),
                ('payment_method', models.CharField(choices=[('eSewa', 'eSewa'), ('Khalti', 'Khalti'), ('ConnectIPS', 'ConnectIPS'), ('Bank Transfer', 'Bank Transfer'), ('Digital Wallet', 'Digital Wallet')], default='eSewa', max_length=50)),
                ('transaction_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('payment_status', models.CharField(choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed'), ('Refunded', 'Refunded')], default='Pending', max_length=20)),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('remarks', models.CharField(blank=True, max_length=255, null=True)),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='passport.applicant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='passport.application')),
            ],
        ),
    ]
