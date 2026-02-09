# Manual migration: Add Node(case, scope) compound index and GraphDelta.case FK

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('graph', '0004_rename_graph_casen_case_id_excluded_idx_graph_casen_case_id_d0b2d7_idx_and_more'),
        ('cases', '0021_remove_workingview_case_and_more'),
    ]

    operations = [
        # Add compound index for Node(case, scope) — optimizes case graph queries
        migrations.AddIndex(
            model_name='node',
            index=models.Index(fields=['case', 'scope'], name='idx_node_case_scope'),
        ),

        # Add optional case FK to GraphDelta
        migrations.AddField(
            model_name='graphdelta',
            name='case',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='graph_deltas',
                to='cases.case',
            ),
        ),
    ]
