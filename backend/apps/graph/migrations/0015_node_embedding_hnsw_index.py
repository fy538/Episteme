"""
Add HNSW index on Node.embedding for fast approximate nearest-neighbor search.

The embedding column already exists (created in 0001_initial) but had no index,
causing pgvector similarity_search to fall back to sequential scans.

HNSW parameters match the project convention (m=16, ef_construction=64)
used on DocumentChunk, ProjectInsight, ResearchResult, and chat model embeddings.
"""
from pgvector.django import HnswIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("graph", "0014_fix_insight_source_type_max_length"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="node",
            index=HnswIndex(
                fields=["embedding"],
                m=16,
                ef_construction=64,
                name="node_embedding_hnsw_idx",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
