from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='detectederror',
            name='spacy_pos_tag',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='detectederror',
            name='error_context',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
