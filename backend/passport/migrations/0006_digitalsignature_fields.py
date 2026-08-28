from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0005_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='digitalsignature',
            name='signing_authority',
            field=models.CharField(default='Department of Passports, Government of Nepal', max_length=200),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='certificate_serial',
            field=models.CharField(default='NPL-DOP-PKI-2026-001', max_length=100),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='algorithm',
            field=models.CharField(default='RSA-SHA256', max_length=50),
        ),
        migrations.AddField(
            model_name='digitalsignature',
            name='signed_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='digitalsignature',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
    ]
