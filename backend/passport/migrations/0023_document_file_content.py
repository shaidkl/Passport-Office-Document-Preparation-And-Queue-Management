from django.db import migrations, models


def preserve_existing_document_files(apps, schema_editor):
    Document = apps.get_model('passport', 'Document')
    for document in Document.objects.exclude(file_path='').iterator():
        try:
            with document.file_path.open('rb') as source:
                content = source.read()
        except (FileNotFoundError, OSError, ValueError):
            continue
        if content:
            Document.objects.filter(pk=document.pk).update(file_content=content)


class Migration(migrations.Migration):

    dependencies = [
        ('passport', '0022_applicant_email_verified_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='file_content',
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(
            preserve_existing_document_files,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
