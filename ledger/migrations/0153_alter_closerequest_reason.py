# Generated by Django 4.1.3 on 2023-01-03 17:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0152_merge_20221228_1325'),
    ]

    operations = [
        migrations.AlterField(
            model_name='closerequest',
            name='reason',
            field=models.CharField(choices=[('liquid', 'liquid'), ('user', 'user'), ('system', 'system')], max_length=8),
        ),
    ]
