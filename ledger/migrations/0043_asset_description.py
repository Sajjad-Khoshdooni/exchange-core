# Generated by Django 4.0 on 2022-02-07 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0042_auto_20220206_1739'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
