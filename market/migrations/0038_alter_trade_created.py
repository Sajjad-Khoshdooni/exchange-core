# Generated by Django 4.1.3 on 2023-01-26 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0037_partition_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trade',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]