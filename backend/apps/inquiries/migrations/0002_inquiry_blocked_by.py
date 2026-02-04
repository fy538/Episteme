# Generated manually for inquiry dependencies

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inquiries', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='blocked_by',
            field=models.ManyToManyField(
                blank=True,
                help_text='Inquiries that must be resolved before this one can be resolved',
                related_name='blocks',
                to='inquiries.inquiry',
            ),
        ),
    ]
