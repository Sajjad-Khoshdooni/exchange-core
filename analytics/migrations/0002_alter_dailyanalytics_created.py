# Generated by Django 4.1.3 on 2023-04-06 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyanalytics',
            name='created',
            field=models.DateTimeField(db_index=True, unique=True),
        ),
    ]
