# Generated by Django 2.1.3 on 2018-11-27 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djasana", "0010_expands_resource_subtype"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="dependencies",
            field=models.ManyToManyField(related_name="dependents", to="djasana.Task"),
        ),
    ]
