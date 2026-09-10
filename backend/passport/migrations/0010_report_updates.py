from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0009_payment_system_enhancements'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='report_data',
        ),
        migrations.RemoveField(
            model_name='report',
            name='report_date',
        ),
        migrations.AddField(
            model_name='report',
            name='generated_date',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='data_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
