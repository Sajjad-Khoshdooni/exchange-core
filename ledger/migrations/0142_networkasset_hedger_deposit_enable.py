# Generated by Django 4.0 on 2022-11-08 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0140_remove_asset_candidate'),
    ]

    operations = [
        migrations.AddField(
            model_name='networkasset',
            name='hedger_deposit_enable',
            field=models.BooleanField(default=True),
        ),
    ]
