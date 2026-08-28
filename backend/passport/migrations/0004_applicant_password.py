from django.db import migrations, models
def set_existing_passwords(apps, schema_editor):
    Applicant = apps.get_model('passport', 'Applicant')
    Applicant.objects.all().update(password='!')


class Migration(migrations.Migration):
    dependencies = [
        ('passport', '0003_authtoken_notification_applicant_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='password',
            field=models.CharField(default='!', max_length=128),
        ),
        migrations.RunPython(set_existing_passwords, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='applicant',
            name='password',
            field=models.CharField(max_length=128),
        ),
    ]