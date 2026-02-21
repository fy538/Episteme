"""
Migrate Case.embedding from JSONField to pgvector VectorField.

Strategy (mirrors projects/0013_chunk_embedding_to_vector):
1. Rename embedding → embedding_json
2. Add new VectorField(dimensions=384) as embedding_vec
3. Copy JSON data → vector data
4. Drop old JSON column
5. Rename embedding_vec → embedding
6. Add HNSW index for fast cosine similarity search
"""
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations, models


def convert_json_to_vector(apps, schema_editor):
    """Copy JSON embedding arrays to the new vector column."""
    Case = apps.get_model('cases', 'Case')

    batch_size = 500
    cases = Case.objects.exclude(
        embedding_json__isnull=True,
    ).only('id', 'embedding_json')

    to_update = []
    for case in cases.iterator(chunk_size=batch_size):
        data = case.embedding_json
        if isinstance(data, list) and len(data) == 384:
            case.embedding_vec = data
            to_update.append(case)

        if len(to_update) >= batch_size:
            Case.objects.bulk_update(to_update, ['embedding_vec'])
            to_update = []

    if to_update:
        Case.objects.bulk_update(to_update, ['embedding_vec'])


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0027_planversion_trigger_type_generation_context'),
    ]

    operations = [
        # 1. Rename current JSONField so we can reuse the name
        migrations.RenameField(
            model_name='case',
            old_name='embedding',
            new_name='embedding_json',
        ),
        # 2. Add new VectorField
        migrations.AddField(
            model_name='case',
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
            model_name='case',
            name='embedding_json',
        ),
        # 5. Rename new column to 'embedding'
        migrations.RenameField(
            model_name='case',
            old_name='embedding_vec',
            new_name='embedding',
        ),
        # 6. Add HNSW index for fast cosine similarity
        migrations.AddIndex(
            model_name='case',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='case_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
