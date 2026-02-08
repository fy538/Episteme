"""
Add intelligence_config and investigation_preferences JSONFields to Case.

These enable per-case configuration of:
- AI behavior toggles (auto-validate, background research, gap detection)
- Investigation rigor, evidence thresholds, and section lock overrides
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0017_briefsection_user_confidence'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='intelligence_config',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Per-case AI behavior config: {auto_validate, background_research, gap_detection}',
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='investigation_preferences',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Per-case investigation prefs: {rigor, evidence_threshold, disable_locks}',
            ),
        ),
    ]
