"""
Remove projects.Evidence model, Document.evidence_count, Document.signals_extracted.

Graph Node(type='evidence') replaces the projects.Evidence model.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_rename_projects_do_project_scope_idx_projects_do_project_0e01af_idx'),
    ]

    operations = [
        # Drop the Evidence model
        migrations.DeleteModel(
            name='Evidence',
        ),
    ]
