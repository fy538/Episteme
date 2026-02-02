# Migration for adding thread_type and updating primary_case relationship

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        ('cases', '0004_case_active_skills_case_based_on_skill_and_more'),
    ]

    operations = [
        # Add thread_type field to ChatThread
        migrations.AddField(
            model_name='chatthread',
            name='thread_type',
            field=models.CharField(
                choices=[
                    ('general', 'General Discussion'),
                    ('research', 'Research Thread'),
                    ('inquiry', 'Inquiry-Specific'),
                    ('document', 'Document Analysis'),
                ],
                default='general',
                help_text='Type of conversation thread',
                max_length=20
            ),
        ),
        
        # Update ChatThread.primary_case related_name to support multiple threads per case
        migrations.AlterField(
            model_name='chatthread',
            name='primary_case',
            field=models.ForeignKey(
                blank=True,
                help_text='Case this thread is about (many threads per case supported)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chat_threads',
                to='cases.case'
            ),
        ),
    ]
