# Generated manually for case-level graph scoping

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0007_document_extraction_error_document_extraction_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="scope",
            field=models.CharField(
                choices=[("project", "Project"), ("case", "Case")],
                default="project",
                help_text="project = feeds project graph; case = only visible within owning case",
                max_length=16,
            ),
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(
                fields=["project", "scope"],
                name="projects_do_project_scope_idx",
            ),
        ),
    ]
