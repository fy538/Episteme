# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_rename_chat_messag_content_idx_chat_messag_content_dc73a7_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatthread',
            name='title_manually_edited',
            field=models.BooleanField(
                default=False,
                help_text='True if user manually renamed this thread; suppresses auto-title updates',
            ),
        ),
    ]
