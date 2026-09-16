from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('passport', '0021_sequential_passport_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='email_verified_at',
            field=models.DateTimeField(
                blank=True,
                default=django.utils.timezone.now,
                null=True,
            ),
        ),
    ]
