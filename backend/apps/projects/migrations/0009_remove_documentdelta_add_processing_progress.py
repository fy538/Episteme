# Remove DocumentDelta model and add processing_progress field to Document

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0008_document_scope"),
    ]

    operations = [
        # Drop the DocumentDelta table (reverses 0005 + 0006)
        migrations.DeleteModel(
            name="DocumentDelta",
        ),
        # Add processing_progress JSONField for SSE streaming
        migrations.AddField(
            model_name="document",
            name="processing_progress",
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text="Progressive processing status for SSE streaming",
            ),
        ),
    ]
