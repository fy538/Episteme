# Generated manually for decision frame fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0005_require_project_remove_linked_thread'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='decision_question',
            field=models.TextField(blank=True, help_text="Core question being decided (e.g., 'Should we acquire CompanyX?')"),
        ),
        migrations.AddField(
            model_name='case',
            name='constraints',
            field=models.JSONField(default=list, help_text='Constraints on the decision: [{type, description}]'),
        ),
        migrations.AddField(
            model_name='case',
            name='success_criteria',
            field=models.JSONField(default=list, help_text='Success criteria: [{criterion, measurable, target}]'),
        ),
        migrations.AddField(
            model_name='case',
            name='stakeholders',
            field=models.JSONField(default=list, help_text='Stakeholders: [{name, interest, influence}]'),
        ),
    ]
