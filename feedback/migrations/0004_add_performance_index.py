from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Composite index on (submission, error_category) for the hot query path used
    in compute_summary_for_submission, get_student_progress, and
    get_classroom_patterns (NFR-1.1 / NFR-1.2).
    """

    dependencies = [
        ('feedback', '0003_detectederror_resolution_metadata'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='detectederror',
            index=models.Index(
                fields=['submission', 'error_category'],
                name='detectederror_sub_cat_idx',
            ),
        ),
    ]
