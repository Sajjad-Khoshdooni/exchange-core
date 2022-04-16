# Generated by Django 4.0 on 2022-04-16 09:58

from django.db import migrations, models

from ledger.models import Asset
from market.models import FillOrder


def populate_fill_order_values(apps, schema_editor):
    for fill in FillOrder.objects.all():
        fill.irt_value = fill.price * fill.amount

        if fill.symbol.base_asset.symbol == Asset.USDT:
            fill.irt_value *= 27000

        fill.save()


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0008_set_maker_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='fillorder',
            name='irt_value',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.RunPython(
            code=populate_fill_order_values, reverse_code=migrations.RunPython.noop
        )
    ]