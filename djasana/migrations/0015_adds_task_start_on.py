# Generated by Django 2.0.4 on 2018-05-01 09:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djasana", "0014_user_email_allows_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="start_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
