# Add full-text search (tsvector) to DocumentChunk for BM25-style keyword retrieval.
#
# Uses a PostgreSQL generated column so the search_vector is auto-maintained
# whenever chunk_text is updated — zero application code needed for writes.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0016_remove_documentchunk_projects_do_documen_8c450a_idx_and_more"),
    ]

    operations = [
        # Add the generated tsvector column
        migrations.RunSQL(
            sql="""
                ALTER TABLE projects_documentchunk
                ADD COLUMN IF NOT EXISTS search_vector tsvector
                GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED;
            """,
            reverse_sql="""
                ALTER TABLE projects_documentchunk
                DROP COLUMN IF EXISTS search_vector;
            """,
        ),
        # Create GIN index for fast full-text queries
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS chunk_search_vector_gin_idx
                ON projects_documentchunk USING GIN (search_vector);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS chunk_search_vector_gin_idx;
            """,
        ),
    ]
