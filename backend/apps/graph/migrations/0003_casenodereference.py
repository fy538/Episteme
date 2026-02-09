# Generated manually for case-level graph scoping

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0021_remove_workingview_case_and_more"),
        ("graph", "0002_cascade_source_document"),
    ]

    operations = [
        migrations.CreateModel(
            name="CaseNodeReference",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "inclusion_type",
                    models.CharField(
                        choices=[
                            ("auto", "Auto-pulled by similarity"),
                            ("manual", "Manually added by user"),
                            ("document", "From document integration"),
                        ],
                        default="auto",
                        max_length=16,
                    ),
                ),
                (
                    "relevance",
                    models.FloatField(
                        default=0.0,
                        help_text="Similarity score when auto-pulled (0.0-1.0)",
                    ),
                ),
                (
                    "excluded",
                    models.BooleanField(
                        default=False,
                        help_text="User soft-hid this node from case view",
                    ),
                ),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="node_references",
                        to="cases.case",
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="case_references",
                        to="graph.node",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="casenodereference",
            constraint=models.UniqueConstraint(
                fields=("case", "node"), name="unique_case_node_ref"
            ),
        ),
        migrations.AddIndex(
            model_name="casenodereference",
            index=models.Index(
                fields=["case", "excluded"],
                name="graph_casen_case_id_excluded_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="casenodereference",
            index=models.Index(
                fields=["node"],
                name="graph_casen_node_id_idx",
            ),
        ),
    ]
