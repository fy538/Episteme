"""
Add resolution_type and resolution_profile fields to DecisionRecord.

resolution_type distinguishes how a case was resolved (decision, conclusion,
shelved, wrong_question). Defaults to 'decision' for backward compatibility.

resolution_profile stores an LLM-generated narrative characterization of
the resolution quality, replacing the numerical confidence score in the UI.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0030_decisionrecord_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='decisionrecord',
            name='resolution_type',
            field=models.CharField(
                choices=[
                    ('decision', 'Decision'),
                    ('conclusion', 'Conclusion'),
                    ('shelved', 'Shelved'),
                    ('wrong_question', 'Wrong Question'),
                ],
                default='decision',
                help_text='How this case was resolved',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='decisionrecord',
            name='resolution_profile',
            field=models.TextField(
                blank=True,
                default='',
                help_text='LLM-generated narrative characterization of the resolution quality',
            ),
        ),
    ]
