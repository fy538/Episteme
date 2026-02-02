# Migration for adding rich message support (content_type and structured_content)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_merge_20260201_2333'),
    ]

    operations = [
        # Add content_type field to Message
        migrations.AddField(
            model_name='message',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('text', 'Plain Text'),
                    ('card_signal_extraction', 'Signal Extraction Card'),
                    ('card_case_suggestion', 'Case Suggestion Card'),
                    ('card_structure_preview', 'Structure Preview Card'),
                    ('card_research_status', 'Research Status Card'),
                    ('card_evidence_map', 'Evidence Map Card'),
                    ('card_action_prompt', 'Action Prompt Card'),
                    ('card_assumption_validator', 'Assumption Validator Card'),
                ],
                default='text',
                help_text='Type of message content (text or card)',
                max_length=50
            ),
        ),
        
        # Add structured_content field to Message
        migrations.AddField(
            model_name='message',
            name='structured_content',
            field=models.JSONField(
                blank=True,
                default=None,
                help_text='Structured data for rich message types (cards, forms, etc.)',
                null=True
            ),
        ),
        
        # Add index on content_type for efficient filtering
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['content_type'], name='chat_messag_content_idx'),
        ),
    ]
