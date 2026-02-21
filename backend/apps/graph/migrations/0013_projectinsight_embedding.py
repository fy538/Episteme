"""
Add embedding VectorField to ProjectInsight for semantic search.
"""
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('graph', '0012_projectorientation_user_guidance_generation_context'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectinsight',
            name='embedding',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from sentence-transformers',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='projectinsight',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='insight_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
