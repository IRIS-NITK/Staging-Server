# Generated by Django 4.1.4 on 2023-01-21 12:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_runninginstance_dockerfile_path'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='runninginstance',
            name='dockerfile_path',
        ),
    ]
