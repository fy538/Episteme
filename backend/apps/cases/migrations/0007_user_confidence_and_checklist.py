# Generated migration for user confidence and readiness checklist

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0006_case_decision_frame_fields'),
        ('inquiries', '0002_inquiry_blocked_by'),
    ]

    operations = [
        # Add user confidence fields to Case
        migrations.AddField(
            model_name='case',
            name='user_confidence',
            field=models.IntegerField(
                blank=True,
                help_text="User's self-assessed confidence (0-100)",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100)
                ],
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='user_confidence_updated_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When user last updated their confidence',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='what_would_change_mind',
            field=models.TextField(
                blank=True,
                help_text="User's answer to 'What would change your mind?'",
            ),
        ),
        # Create ReadinessChecklistItem model
        migrations.CreateModel(
            name='ReadinessChecklistItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.TextField(help_text='What needs to be true/done before deciding')),
                ('is_required', models.BooleanField(default=True, help_text="Whether this item must be complete to be 'ready'")),
                ('is_complete', models.BooleanField(default=False, help_text='User marks this complete when satisfied')),
                ('completed_at', models.DateTimeField(blank=True, help_text='When this item was marked complete', null=True)),
                ('order', models.IntegerField(default=0, help_text='Display order')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='readiness_checklist', to='cases.case')),
                ('linked_inquiry', models.ForeignKey(blank=True, help_text='Inquiry that validates this criterion', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='readiness_items', to='inquiries.inquiry')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='readinesschecklistitem',
            index=models.Index(fields=['case', 'order'], name='cases_readi_case_id_6c9c8a_idx'),
        ),
    ]
