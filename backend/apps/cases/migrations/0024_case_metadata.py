"""Add metadata JSONField to Case for extraction pipeline state and analysis results."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0023_rename_to_working_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Flexible metadata: extraction status, analysis results, companion origin, etc.',
            ),
        ),
    ]
