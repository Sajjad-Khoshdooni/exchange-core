# Generated by Django 4.0 on 2022-02-05 10:42
import math

from django.db import migrations, models


def populate_precision(apps, schema_editor):
    Asset = apps.get_model('ledger', 'Asset')

    for asset in Asset.objects.all():
        asset.precision = int(-math.log10(asset.trade_quantity_step))
        asset.save()


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0034_transfer_is_fee_alter_transfer_block_hash_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='precision',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.RunPython(populate_precision, migrations.RunPython.noop)
    ]
