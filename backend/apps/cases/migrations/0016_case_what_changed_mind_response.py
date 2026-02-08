"""
Add what_changed_mind_response and what_changed_mind_response_at fields to Case model.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0015_case_premortem'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='what_changed_mind_response',
            field=models.CharField(
                blank=True,
                choices=[
                    ('updated_view', 'Yes, and I updated my view'),
                    ('proceeding_anyway', "Yes, but I'm proceeding anyway"),
                    ('not_materialized', 'No, none of this materialized'),
                ],
                default='',
                help_text="User's response when their earlier 'what would change your mind' is resurfaced",
                max_length=50,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='case',
            name='what_changed_mind_response_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the user responded to the resurface prompt',
            ),
        ),
    ]
