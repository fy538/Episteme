"""
Add embedding VectorField to DecisionRecord for semantic search.
"""
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0028_case_embedding_to_vector'),
    ]

    operations = [
        migrations.AddField(
            model_name='decisionrecord',
            name='embedding',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from sentence-transformers',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='decisionrecord',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='decision_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
