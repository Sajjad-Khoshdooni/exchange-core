# Generated by Django 4.0 on 2022-02-06 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0037_alter_asset_options_rename_important_asset_trend'),
    ]

    operations = [
        migrations.AddField(
            model_name='network',
            name='address_regex',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='transfer',
            name='handling',
            field=models.BooleanField(default=False),
        ),
    ]
