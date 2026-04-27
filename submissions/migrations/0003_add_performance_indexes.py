from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Composite index for the hot query path: submissions by student ordered by
    date, used in get_student_progress (NFR-1.2).
    """

    dependencies = [
        ('submissions', '0002_textsubmission_analysis_task_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='textsubmission',
            index=models.Index(
                fields=['student', 'submitted_at'],
                name='submission_student_date_idx',
            ),
        ),
    ]
