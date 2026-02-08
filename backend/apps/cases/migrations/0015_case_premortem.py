"""
Add premortem_text and premortem_at fields to Case model.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0014_investigation_plan'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='premortem_text',
            field=models.TextField(
                blank=True,
                default='',
                help_text="User's premortem: imagined reason for future failure",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='case',
            name='premortem_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the premortem was written',
            ),
        ),
    ]
