"""
Migrate resolution_type from 4-choice (decision, conclusion, shelved, wrong_question)
to 2-choice (resolved, closed).

Mapping:
  decision      → resolved
  conclusion    → resolved
  shelved       → closed
  wrong_question → closed
"""
from django.db import migrations, models


def migrate_resolution_types(apps, schema_editor):
    DecisionRecord = apps.get_model('cases', 'DecisionRecord')
    # Map old values to new
    DecisionRecord.objects.filter(
        resolution_type__in=['decision', 'conclusion']
    ).update(resolution_type='resolved')
    DecisionRecord.objects.filter(
        resolution_type__in=['shelved', 'wrong_question']
    ).update(resolution_type='closed')


def reverse_migration(apps, schema_editor):
    # Best-effort reverse: resolved → decision, closed → shelved
    DecisionRecord = apps.get_model('cases', 'DecisionRecord')
    DecisionRecord.objects.filter(resolution_type='resolved').update(resolution_type='decision')
    DecisionRecord.objects.filter(resolution_type='closed').update(resolution_type='shelved')


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0031_decisionrecord_resolution_fields'),
    ]

    operations = [
        # First: data migration (remap old values)
        migrations.RunPython(migrate_resolution_types, reverse_migration),
        # Then: alter field to new choices + default
        migrations.AlterField(
            model_name='decisionrecord',
            name='resolution_type',
            field=models.CharField(
                choices=[('resolved', 'Resolved'), ('closed', 'Closed')],
                default='resolved',
                help_text='How this case was resolved',
                max_length=20,
            ),
        ),
    ]
