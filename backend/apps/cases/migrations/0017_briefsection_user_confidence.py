"""
Add user_confidence and user_confidence_at fields to BriefSection model.

Supports decomposed section judgment — users rate confidence per-section
during synthesizing stage.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0016_case_what_changed_mind_response'),
    ]

    operations = [
        migrations.AddField(
            model_name='briefsection',
            name='user_confidence',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="User's confidence in this section's conclusion (1-4)",
            ),
        ),
        migrations.AddField(
            model_name='briefsection',
            name='user_confidence_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When user last rated this section',
            ),
        ),
    ]
