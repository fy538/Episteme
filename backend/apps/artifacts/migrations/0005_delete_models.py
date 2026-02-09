"""
Delete Artifact and ArtifactVersion models.

The Artifact system has been consolidated into WorkingDocument.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('artifacts', '0004_artifact_input_nodes'),
    ]

    operations = [
        # Remove M2M tables first (input_nodes, skills_used)
        migrations.RemoveField(
            model_name='artifact',
            name='input_nodes',
        ),
        migrations.RemoveField(
            model_name='artifact',
            name='skills_used',
        ),
        # Delete ArtifactVersion first (has FK to Artifact)
        migrations.DeleteModel(
            name='ArtifactVersion',
        ),
        # Delete Artifact
        migrations.DeleteModel(
            name='Artifact',
        ),
    ]
