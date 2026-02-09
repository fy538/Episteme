"""
Migrate DocumentChunk.embedding from JSONField to pgvector VectorField.

Strategy:
1. Add new VectorField column (embedding_vec)
2. Copy JSON data → vector data
3. Drop old JSON column
4. Rename embedding_vec → embedding
5. Add HNSW index for fast cosine similarity search
"""
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations, models


def convert_json_to_vector(apps, schema_editor):
    """Copy JSON embedding arrays to the new vector column."""
    DocumentChunk = apps.get_model('projects', 'DocumentChunk')

    # Process in batches to avoid loading everything into memory
    batch_size = 500
    chunks = DocumentChunk.objects.exclude(
        embedding_json__isnull=True,
    ).only('id', 'embedding_json')

    to_update = []
    for chunk in chunks.iterator(chunk_size=batch_size):
        data = chunk.embedding_json
        if isinstance(data, list) and len(data) == 384:
            chunk.embedding_vec = data
            to_update.append(chunk)

        if len(to_update) >= batch_size:
            DocumentChunk.objects.bulk_update(to_update, ['embedding_vec'])
            to_update = []

    if to_update:
        DocumentChunk.objects.bulk_update(to_update, ['embedding_vec'])


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0012_remove_document_evidence_count_and_more'),
    ]

    operations = [
        # 1. Rename current JSONField so we can reuse the name
        migrations.RenameField(
            model_name='documentchunk',
            old_name='embedding',
            new_name='embedding_json',
        ),
        # 2. Add new VectorField
        migrations.AddField(
            model_name='documentchunk',
            name='embedding_vec',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from sentence-transformers',
                null=True,
            ),
        ),
        # 3. Copy data
        migrations.RunPython(
            convert_json_to_vector,
            reverse_code=migrations.RunPython.noop,
        ),
        # 4. Drop old JSON column
        migrations.RemoveField(
            model_name='documentchunk',
            name='embedding_json',
        ),
        # 5. Rename new column to 'embedding'
        migrations.RenameField(
            model_name='documentchunk',
            old_name='embedding_vec',
            new_name='embedding',
        ),
        # 6. Add HNSW index for fast cosine similarity
        migrations.AddIndex(
            model_name='documentchunk',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='chunk_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
