# Generated migration for analysis_task_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='textsubmission',
            name='analysis_task_id',
            field=models.CharField(
                blank=True,
                help_text='Celery task ID for async analysis',
                max_length=255,
                null=True,
            ),
        ),
    ]
