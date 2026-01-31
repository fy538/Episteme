from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        ("projects", "__first__"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE chat_chatthread
            ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false;

            ALTER TABLE chat_chatthread
            ADD COLUMN IF NOT EXISTS project_id uuid NULL;

            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'chat_chatthread_project_id_fk'
                ) THEN
                    ALTER TABLE chat_chatthread
                    ADD CONSTRAINT chat_chatthread_project_id_fk
                    FOREIGN KEY (project_id)
                    REFERENCES projects_project (id)
                    DEFERRABLE INITIALLY DEFERRED;
                END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE chat_chatthread
            DROP CONSTRAINT IF EXISTS chat_chatthread_project_id_fk;

            ALTER TABLE chat_chatthread
            DROP COLUMN IF EXISTS project_id;

            ALTER TABLE chat_chatthread
            DROP COLUMN IF EXISTS archived;
            """,
        )
    ]
