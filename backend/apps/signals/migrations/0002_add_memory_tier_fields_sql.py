# Manual migration to add memory tier fields to existing Signal table
# This uses raw SQL because the fields are already in the model but not in the DB

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0001_initial'),
    ]

    operations = [
        # Add temperature field
        migrations.RunSQL(
            sql="""
            ALTER TABLE signals_signal 
            ADD COLUMN IF NOT EXISTS temperature VARCHAR(10) NOT NULL DEFAULT 'warm';
            
            CREATE INDEX IF NOT EXISTS signals_sig_tempera_2142dd_idx 
            ON signals_signal (temperature, case_id);
            
            CREATE INDEX IF NOT EXISTS signals_sig_thread__da11d1_idx 
            ON signals_signal (thread_id, temperature);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS signals_sig_tempera_2142dd_idx;
            DROP INDEX IF EXISTS signals_sig_thread__da11d1_idx;
            ALTER TABLE signals_signal DROP COLUMN IF EXISTS temperature;
            """
        ),
        
        # Add access tracking fields
        migrations.RunSQL(
            sql="""
            ALTER TABLE signals_signal 
            ADD COLUMN IF NOT EXISTS access_count INTEGER NOT NULL DEFAULT 0;
            
            ALTER TABLE signals_signal 
            ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP WITH TIME ZONE NULL;
            
            CREATE INDEX IF NOT EXISTS signals_sig_access__aeb012_idx 
            ON signals_signal (access_count, last_accessed);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS signals_sig_access__aeb012_idx;
            ALTER TABLE signals_signal DROP COLUMN IF EXISTS last_accessed;
            ALTER TABLE signals_signal DROP COLUMN IF EXISTS access_count;
            """
        ),
        
        # Add pinned_at field
        migrations.RunSQL(
            sql="""
            ALTER TABLE signals_signal 
            ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMP WITH TIME ZONE NULL;
            """,
            reverse_sql="""
            ALTER TABLE signals_signal DROP COLUMN IF EXISTS pinned_at;
            """
        ),
    ]
