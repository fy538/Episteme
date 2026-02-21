"""
Add embedding VectorField to ResearchResult for semantic search.
"""
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0009_conversationstructure_rolling_digest'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchresult',
            name='embedding',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from sentence-transformers',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='researchresult',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='research_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
