# Generated by Django 4.1.4 on 2023-01-07 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_deploytemplate_docker_env_vars'),
    ]

    operations = [
        migrations.AddField(
            model_name='runninginstance',
            name='exposed_port',
            field=models.IntegerField(default=3000),
        ),
        migrations.AddField(
            model_name='runninginstance',
            name='internal_port',
            field=models.IntegerField(default=80),
        ),
        migrations.AlterField(
            model_name='deploytemplate',
            name='access_token',
            field=models.TextField(blank=True, max_length=50, null=True, verbose_name='Access Token'),
        ),
    ]