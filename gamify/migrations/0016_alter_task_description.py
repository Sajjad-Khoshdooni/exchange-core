# Generated by Django 4.1.3 on 2023-05-14 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0015_usermission_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='description',
            field=models.CharField(max_length=512),
        ),
    ]