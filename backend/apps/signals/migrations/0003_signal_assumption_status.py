"""
Add assumption_status field to Signal model and new source type choices.

This migration supports unifying the two disconnected assumption systems:
- Plan assumptions (JSON blobs in PlanVersion.content)
- Signal assumptions (type='Assumption' in Signal model)

By adding assumption_status to Signal, the Signal model becomes the single
source of truth for assumption lifecycle state. Plan assumptions will
reference Signal IDs via the signal_id field in the plan JSON.

Note: CharField choices (SignalSourceType additions: 'research', 'grounding')
don't require a migration — Django validates choices at the application layer.
They are documented here for clarity.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0014_investigation_plan'),
        ('signals', '0002_add_composite_indexes'),
    ]

    operations = [
        # Add assumption_status field
        migrations.AddField(
            model_name='signal',
            name='assumption_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('untested', 'Untested'),
                    ('confirmed', 'Confirmed'),
                    ('challenged', 'Challenged'),
                    ('refuted', 'Refuted'),
                ],
                db_index=True,
                help_text='Lifecycle status for Assumption-type signals: untested \u2192 confirmed/challenged/refuted',
                max_length=20,
                null=True,
            ),
        ),
        # Add composite index for case + assumption_status queries
        migrations.AddIndex(
            model_name='signal',
            index=models.Index(
                fields=['case', 'assumption_status'],
                name='signals_sig_case_id_assum_idx',
            ),
        ),
    ]
