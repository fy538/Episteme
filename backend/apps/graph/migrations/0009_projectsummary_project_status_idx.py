"""
Add composite index on (project, status) for ProjectSummary.

This index accelerates mark_stale() exclusion filter, the concurrent-generation
guard (filter status=GENERATING), and cleanup_stuck_generating_summaries.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('graph', '0008_add_thematic_summary_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='projectsummary',
            index=models.Index(
                fields=['project', 'status'],
                name='graph_proj_status_idx',
            ),
        ),
    ]
