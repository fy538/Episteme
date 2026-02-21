"""
Add ConversationEpisode model for conversation memory.

- Creates ConversationEpisode table with all fields + HNSW index on embedding
- Adds embedding VectorField to ConversationStructure + HNSW index
- Adds embedding VectorField to ChatThread + HNSW index
- Adds current_episode FK to ChatThread
- Adds episode FK to Message
"""
import django.db.models.deletion
import uuid
import pgvector.django.vector
from pgvector.django import HnswIndex
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0010_researchresult_embedding'),
    ]

    operations = [
        # ── Create ConversationEpisode table ──────────────────────────────
        migrations.CreateModel(
            name='ConversationEpisode',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4, editable=False,
                    primary_key=True, serialize=False,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('episode_index', models.IntegerField(
                    default=0,
                    help_text='Sequential index within the thread (0-based)',
                )),
                ('topic_label', models.CharField(
                    blank=True, max_length=200,
                    help_text='Brief label for the topic of this episode (3-5 words)',
                )),
                ('content_summary', models.TextField(
                    default='',
                    help_text='Summary of what was discussed/established during this episode',
                )),
                ('message_count', models.IntegerField(
                    default=0,
                    help_text='Number of messages in this episode',
                )),
                ('shift_type', models.CharField(
                    choices=[
                        ('initial', 'Initial'),
                        ('continuous', 'Continuous'),
                        ('partial_shift', 'Partial Shift'),
                        ('discontinuous', 'Discontinuous'),
                    ],
                    default='initial',
                    help_text='How this episode relates to the previous one',
                    max_length=20,
                )),
                ('embedding', pgvector.django.vector.VectorField(
                    blank=True, dimensions=384,
                    help_text='384-dim embedding from content_summary for cross-thread episode search',
                    null=True,
                )),
                ('sealed', models.BooleanField(
                    default=False,
                    help_text='True when this episode is complete and embedding is generated',
                )),
                ('sealed_at', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp when this episode was sealed',
                )),
                # FK fields
                ('thread', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='episodes',
                    to='chat.chatthread',
                )),
                ('start_message', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='chat.message',
                    help_text='First message in this episode',
                )),
                ('end_message', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='chat.message',
                    help_text='Last message in this episode (set when sealed)',
                )),
                ('reasoning_snapshot', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='episode',
                    to='chat.conversationstructure',
                    help_text='ConversationStructure version captured when this episode was sealed',
                )),
            ],
            options={
                'ordering': ['episode_index'],
            },
        ),

        # ── Indexes for ConversationEpisode ───────────────────────────────
        migrations.AddIndex(
            model_name='conversationepisode',
            index=models.Index(
                fields=['thread', 'episode_index'],
                name='chat_conver_thread__8a1c2f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='conversationepisode',
            index=models.Index(
                fields=['thread', '-sealed_at'],
                name='chat_conver_thread__sealed_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='conversationepisode',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='episode_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),

        # ── Add embedding to ConversationStructure ────────────────────────
        migrations.AddField(
            model_name='conversationstructure',
            name='embedding',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from context_summary for cross-thread reasoning search',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='conversationstructure',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='structure_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),

        # ── Add embedding + current_episode to ChatThread ─────────────────
        migrations.AddField(
            model_name='chatthread',
            name='embedding',
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=384,
                help_text='384-dim embedding from latest ConversationStructure.context_summary',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='chatthread',
            index=HnswIndex(
                fields=['embedding'],
                ef_construction=64,
                m=16,
                name='thread_embedding_hnsw_idx',
                opclasses=['vector_cosine_ops'],
            ),
        ),
        migrations.AddField(
            model_name='chatthread',
            name='current_episode',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='chat.conversationepisode',
                help_text='The active episode being accumulated (unsealed)',
            ),
        ),

        # ── Add episode FK to Message ─────────────────────────────────────
        migrations.AddField(
            model_name='message',
            name='episode',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='messages',
                to='chat.conversationepisode',
                help_text='The conversation episode this message belongs to',
            ),
        ),
    ]
