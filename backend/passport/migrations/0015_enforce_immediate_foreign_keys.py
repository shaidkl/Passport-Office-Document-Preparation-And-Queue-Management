# Generated to enforce immediate PostgreSQL Foreign Key constraints

from django.db import migrations

FORWARD_SQL = """
-- 1. Explicitly alter all Foreign Key constraints to NOT DEFERRABLE
ALTER TABLE passport_application ALTER CONSTRAINT passport_application_applicant_id_9b06a516_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_application ALTER CONSTRAINT passport_application_staff_id_0ad6d807_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_document ALTER CONSTRAINT passport_document_application_id_fa1b2980_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_digitalsignature ALTER CONSTRAINT passport_digitalsign_application_id_17540fe3_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_queuetoken ALTER CONSTRAINT passport_queuetoken_application_id_5a75a91c_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_queuetoken ALTER CONSTRAINT passport_queuetoken_staff_id_0d2bee21_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_report ALTER CONSTRAINT passport_report_administrator_id_88c771b5_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_activitylog ALTER CONSTRAINT passport_activitylog_administrator_id_d6bc4b60_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_activitylog ALTER CONSTRAINT passport_activitylog_application_id_6972f813_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_notification ALTER CONSTRAINT passport_notificatio_applicant_id_5e9e0e3f_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_notification ALTER CONSTRAINT passport_notificatio_application_id_fe4ce5fa_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_payment ALTER CONSTRAINT passport_payment_applicant_id_b70c4a65_fk_passport_ NOT DEFERRABLE;
ALTER TABLE passport_payment ALTER CONSTRAINT passport_payment_application_id_d621e8c3_fk_passport_ NOT DEFERRABLE;

-- 2. Dynamic block ensuring any other passport foreign key constraint is also set to NOT DEFERRABLE
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT cl.relname AS table_name, c.conname AS constraint_name
        FROM pg_constraint c
        JOIN pg_class cl ON cl.oid = c.conrelid
        WHERE c.contype = 'f' AND cl.relname LIKE 'passport_%'
    ) LOOP
        EXECUTE format('ALTER TABLE %I ALTER CONSTRAINT %I NOT DEFERRABLE;', r.table_name, r.constraint_name);
    END LOOP;
END $$;
"""

REVERSE_SQL = """
-- Revert constraints back to DEFERRABLE INITIALLY DEFERRED
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT cl.relname AS table_name, c.conname AS constraint_name
        FROM pg_constraint c
        JOIN pg_class cl ON cl.oid = c.conrelid
        WHERE c.contype = 'f' AND cl.relname LIKE 'passport_%'
    ) LOOP
        EXECUTE format('ALTER TABLE %I ALTER CONSTRAINT %I DEFERRABLE INITIALLY DEFERRED;', r.table_name, r.constraint_name);
    END LOOP;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0014_application_application_type_application_expiry_date_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
