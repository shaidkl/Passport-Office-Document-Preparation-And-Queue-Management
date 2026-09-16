from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0016_alter_authtoken_token_alter_payment_payment_method'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE passport_application
                            ADD COLUMN IF NOT EXISTS applying_within_nepal boolean NOT NULL DEFAULT TRUE;
                        ALTER TABLE passport_application
                            ADD COLUMN IF NOT EXISTS appointment_date date NULL;
                        ALTER TABLE passport_application
                            ADD COLUMN IF NOT EXISTS appointment_office varchar(150) NOT NULL
                                DEFAULT 'Department of Passports, Tripureshwor';
                        ALTER TABLE passport_application
                            ADD COLUMN IF NOT EXISTS appointment_time time NULL;
                        ALTER TABLE passport_application
                            ADD COLUMN IF NOT EXISTS national_id_number varchar(50) NULL;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='application',
                    name='applying_within_nepal',
                    field=models.BooleanField(default=True),
                ),
                migrations.AddField(
                    model_name='application',
                    name='appointment_date',
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='application',
                    name='appointment_office',
                    field=models.CharField(
                        default='Department of Passports, Tripureshwor',
                        max_length=150,
                    ),
                ),
                migrations.AddField(
                    model_name='application',
                    name='appointment_time',
                    field=models.TimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='application',
                    name='national_id_number',
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
            ],
        ),
    ]
