from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djasana', '0020_adds_project_default_view'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='has_notifications_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
