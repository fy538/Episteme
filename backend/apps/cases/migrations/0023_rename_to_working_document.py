"""
Rename CaseDocument → WorkingDocument and CaseDocumentVersion → WorkingDocumentVersion.

Also updates related_name fields to match the new naming convention.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0022_alter_briefsection_is_linked'),
        ('inquiries', '0004_inquiryhistory_delete_evidence_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rename models
        migrations.RenameModel(
            old_name='CaseDocument',
            new_name='WorkingDocument',
        ),
        migrations.RenameModel(
            old_name='CaseDocumentVersion',
            new_name='WorkingDocumentVersion',
        ),

        # Update related_name on Case FK
        migrations.AlterField(
            model_name='workingdocument',
            name='case',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='working_documents',
                to='cases.case',
            ),
        ),

        # Update related_name on User FK
        migrations.AlterField(
            model_name='workingdocument',
            name='created_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='created_working_documents',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
