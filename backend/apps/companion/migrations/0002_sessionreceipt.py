# Generated manually for session receipts

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companion', '0001_initial'),
        ('chat', '0005_rename_chat_messag_content_idx_chat_messag_content_dc73a7_idx'),
        ('cases', '0001_initial'),
        ('inquiries', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionReceipt',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('receipt_type', models.CharField(
                    choices=[
                        ('case_created', 'Case Created'),
                        ('signals_extracted', 'Signals Extracted'),
                        ('inquiry_resolved', 'Inquiry Resolved'),
                        ('evidence_added', 'Evidence Added'),
                        ('research_completed', 'Research Completed'),
                    ],
                    help_text='Type of accomplishment',
                    max_length=30
                )),
                ('title', models.CharField(help_text='Brief title describing the accomplishment', max_length=200)),
                ('detail', models.TextField(blank=True, help_text='Additional details about the accomplishment')),
                ('session_started_at', models.DateTimeField(help_text='When the current session started (for grouping receipts)')),
                ('thread', models.ForeignKey(
                    help_text='Thread this receipt belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session_receipts',
                    to='chat.chatthread'
                )),
                ('related_case', models.ForeignKey(
                    blank=True,
                    help_text='Related case if applicable',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='session_receipts',
                    to='cases.case'
                )),
                ('related_inquiry', models.ForeignKey(
                    blank=True,
                    help_text='Related inquiry if applicable',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='session_receipts',
                    to='inquiries.inquiry'
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['thread', '-created_at'], name='companion_s_thread__d2a1b3_idx'),
                    models.Index(fields=['thread', 'session_started_at'], name='companion_s_thread__8f4e2a_idx'),
                    models.Index(fields=['receipt_type', '-created_at'], name='companion_s_receipt_c7b9d1_idx'),
                ],
            },
        ),
    ]
