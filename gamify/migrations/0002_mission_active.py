# Generated by Django 4.0 on 2022-10-02 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mission',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
