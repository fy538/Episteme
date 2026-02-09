"""
Add content_hash field to DocumentChunk for deduplication.

SHA256 of chunk_text — used to skip duplicate chunks when re-uploading
the same document.
"""
import hashlib

from django.db import migrations, models


def backfill_content_hashes(apps, schema_editor):
    """Compute content_hash for existing chunks."""
    DocumentChunk = apps.get_model('projects', 'DocumentChunk')
    batch_size = 500
    to_update = []

    for chunk in DocumentChunk.objects.only('id', 'chunk_text').iterator(chunk_size=batch_size):
        chunk.content_hash = hashlib.sha256(chunk.chunk_text.encode()).hexdigest()
        to_update.append(chunk)

        if len(to_update) >= batch_size:
            DocumentChunk.objects.bulk_update(to_update, ['content_hash'])
            to_update = []

    if to_update:
        DocumentChunk.objects.bulk_update(to_update, ['content_hash'])


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0013_chunk_embedding_to_vector'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentchunk',
            name='content_hash',
            field=models.CharField(
                blank=True, db_index=True, max_length=64,
                help_text='SHA256 of chunk_text for deduplication',
            ),
        ),
        migrations.RunPython(
            backfill_content_hashes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
