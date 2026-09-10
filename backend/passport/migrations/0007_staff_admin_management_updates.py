from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0006_digitalsignature_fields'),
    ]

    operations = [
        # Staff updates
        migrations.AddField(
            model_name='staff',
            name='username',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='department',
            field=models.CharField(default='Document Verification', max_length=100),
        ),
        migrations.AddField(
            model_name='staff',
            name='designation',
            field=models.CharField(default='Verification Officer', max_length=100),
        ),
        migrations.AddField(
            model_name='staff',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),

        # Administrator updates
        migrations.AddField(
            model_name='administrator',
            name='username',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='administrator',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='administrator',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),

        # Application updates
        migrations.AddField(
            model_name='application',
            name='processing_notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
