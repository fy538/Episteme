"""
Add metadata JSONField to DecisionRecord for storing premortem comparisons
and other analysis results.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0029_decisionrecord_embedding'),
    ]

    operations = [
        migrations.AddField(
            model_name='decisionrecord',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Flexible metadata: premortem comparison, analysis results, etc.',
            ),
        ),
    ]
