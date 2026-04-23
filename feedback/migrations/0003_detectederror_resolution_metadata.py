from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0002_detectederror_spacy_pos_tag_error_context'),
    ]

    operations = [
        migrations.AddField(
            model_name='detectederror',
            name='resolution_method',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='detectederror',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]